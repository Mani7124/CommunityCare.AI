from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import json
import sqlite3
import math
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from fastapi import Request # Add this to your FastAPI imports
import time
from datetime import datetime, timedelta

app = FastAPI(title="CommunityCare Agentic Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Vertex AI Client
client = genai.Client(
    vertexai=True,
    project="veo3project-499409",
    location="global",
)

DB_FILE = "community_care.db"

def init_db():
    """Initializes the SQLite database with tracking metrics."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            severity_score INTEGER,
            description TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'Open',
            upvote_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()
# --- RATE LIMITER ---
USER_UPLOADS = {}
MAX_UPLOADS_PER_MINUTE = 3

def check_rate_limit(ip_address: str):
    """Prevents spam uploads from the same user."""
    current_time = time.time()
    if ip_address not in USER_UPLOADS:
        USER_UPLOADS[ip_address] = []
    
    # Clean up uploads older than 60 seconds
    USER_UPLOADS[ip_address] = [t for t in USER_UPLOADS[ip_address] if current_time - t < 60]
    
    if len(USER_UPLOADS[ip_address]) >= MAX_UPLOADS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Spam protection active. Please wait a minute before reporting another issue.")
    
    USER_UPLOADS[ip_address].append(current_time)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine formula to compute distance between two coordinates in meters."""
    R = 6371000  # Radius of the Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- BUREAUCRATIC ROUTING DICTIONARY ---
# For the demo, put YOUR test email here so you can show the judges the emails arriving live!
DEPARTMENT_EMAILS = {
    "Water Leak": "projecttester.ai@gmail.com", 
    "Road Hazard": "projecttester.ai@gmail.com",
    "Electrical": "projecttester.ai@gmail.com",
    "Waste Management": "projecttester.ai@gmail.com",
    "Other": "projecttester.ai@gmail.com"
}

def dispatch_department_email(category, severity, description, lat, lon, image_data, mime_type):
    """Agentic function to draft and send formal complaints."""
    sender_email = "projecttester.ai@gmail.com" # The email you got the App Password for
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")
    target_email = DEPARTMENT_EMAILS.get(category, DEPARTMENT_EMAILS["Other"])

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = target_email
    msg['Subject'] = f"URGENT Civic Alert: {category} (Severity {severity}/10)"

    # The auto-generated formal complaint body
    body = f"""
Dear Department Official,

An urgent civic infrastructure issue has been reported and verified by the CommunityHero AI system.

ISSUE DETAILS:
-----------------------------------------
Category: {category}
Severity Score: {severity}/10
Automated Assessment: {description}
Coordinates: {lat}, {lon}

ACTION REQUIRED:
View exact location on Google Maps: http://maps.google.com/?q={lat},{lon}

Photographic evidence is attached to this email. 
Please update the resolution status in the municipal portal.

Automated via CommunityHero.ai
    """
    msg.attach(MIMEText(body, 'plain'))

    # Attach the user's uploaded image
    image_attachment = MIMEImage(image_data, _subtype=mime_type.split('/')[1])
    image_attachment.add_header('Content-Disposition', 'attachment', filename="verified_evidence.jpg")
    msg.attach(image_attachment)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Success: Dispatched email to {target_email}")
    except Exception as e:
        print(f"Failed to dispatch email: {e}")

@app.post("/api/report-issue")
async def analyze_and_route_issue(
    request: Request,
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    try:
        image_data = await file.read()
        client_ip = request.client.host
        check_rate_limit(client_ip)
        # 1. Fetch existing open issues to run deduplication check
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, latitude, longitude, upvote_count FROM issues WHERE status = 'Open'")
        existing_issues = cursor.fetchall()

        # 2. Check for duplicates within a 20-meter radius
        DEDUPLICATION_RADIUS_METERS = 20.0
        for issue_id, ex_lat, ex_lon, upvotes in existing_issues:
            distance = calculate_distance(latitude, longitude, ex_lat, ex_lon)
            if distance <= DEDUPLICATION_RADIUS_METERS:
                new_upvotes = upvotes + 1
                cursor.execute(
                    "UPDATE issues SET upvote_count = ? WHERE id = ?", 
                    (new_upvotes, issue_id)
                )
                conn.commit()
                conn.close()
                return {
                    "status": "deduplicated",
                    "message": "Similar issue already reported nearby. Added your report as community validation!",
                    "data": {"id": issue_id, "upvotes": new_upvotes}
                }

        # 3. If unique issue, invoke Gemini 3.5 Flash for Multimodal analysis
        prompt = """
        You are an expert municipal infrastructure inspector. 
        Analyze this image and identify the primary civic issue.
        You must respond ONLY with a valid JSON object using this exact schema:
        {
            "category": "Water Leak" | "Road Hazard" | "Electrical" | "Waste Management" | "Other",
            "severity_score": <int from 1 to 10>,
            "description": "<One formal, concise sentence describing the damage>"
        }
        """
        
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=image_data, mime_type=file.content_type)
            ]
        )
        
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        ai_data = json.loads(raw_text)
        
        # 4. Save the unique, newly verified issue into database
        cursor.execute("""
            INSERT INTO issues (category, severity_score, description, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
        """, (ai_data["category"], ai_data["severity_score"], ai_data["description"], latitude, longitude))
        
        conn.commit()
        conn.close()
        
        # 5. AGENTIC ACTION: Trigger the Bureaucratic Router!
        dispatch_department_email(
            category=ai_data["category"],
            severity=ai_data["severity_score"],
            description=ai_data["description"],
            lat=latitude,
            lon=longitude,
            image_data=image_data,
            mime_type=file.content_type
        )
        
        return {"status": "success", "message": "New unique issue recorded.", "data": ai_data}
        
    except Exception as e:
        if 'conn' in locals(): conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard-metrics")
def get_metrics():
    """Fetches all parsed issues for the Transparent Public Map Dashboard."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, severity_score, description, latitude, longitude, status, upvote_count FROM issues")
    rows = cursor.fetchall()
    conn.close()
    issues_list = []
    for r in rows:
        issues_list.append({
            "id": r[0], "category": r[1], "severity_score": r[2],
            "description": r[3], "latitude": r[4], "longitude": r[5],
            "status": r[6], "upvote_count": r[7]
        })
    return issues_list
def dispatch_escalation_email(issue_id, category):
    """Sends a harsh email to the Mayor/Higher Official if ignored or falsified."""
    sender_email = "your_test_email@gmail.com" 
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")
    target_email = "your_test_email@gmail.com" # Put your email here to test
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = target_email
    msg['Subject'] = f"ESCALATION: Unresolved Civic Grievance #{issue_id}"
    
    body = f"Higher Official,\n\nTicket #{issue_id} ({category}) was marked as resolved by the department, but the community has flagged it as STILL BROKEN.\n\nImmediate intervention required."
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Escalation failed: {e}")

@app.post("/api/admin-resolve/{issue_id}")
def admin_mark_resolved(issue_id: int):
    """Simulates the municipal department marking the issue as fixed."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Move status to Pending Community Verification
    cursor.execute("UPDATE issues SET status = 'Pending Verification' WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Issue marked as resolved by department."}

@app.post("/api/community-verify/{issue_id}")
def community_verify_resolution(issue_id: int, is_fixed: bool = Form(...)):
    """The user feedback loop. Did the city actually fix it?"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if is_fixed:
        cursor.execute("UPDATE issues SET status = 'Closed - Verified' WHERE id = ?", (issue_id,))
        message = "Thank you! Issue permanently closed."
    else:
        # If the city lied about fixing it, trigger escalation!
        cursor.execute("UPDATE issues SET status = 'Escalated' WHERE id = ?", (issue_id,))
        cursor.execute("SELECT category FROM issues WHERE id = ?", (issue_id,))
        category = cursor.fetchone()[0]
        dispatch_escalation_email(issue_id, category)
        message = "Escalation triggered. Higher officials have been notified."
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": message}