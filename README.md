# 🏙️ CommunityCare.ai

An autonomous, AI-driven civic issue dispatcher and tracking radar built to streamline infrastructure reporting between citizens and municipal authorities.

**[🔴 Live Demo](https://communitycare-app-1076612461185.us-central1.run.app)** *(Deployed on Google Cloud Run)*

---

## 🚀 Overview

CommunityCare.ai transforms passive citizen complaints into actionable, deduplicated, and agentically routed workflows. By leveraging multimodal AI (Gemini 1.5 Flash), the platform autonomously categorizes infrastructure hazards (potholes, leaks, broken lights) from citizen photos, calculates severity, and drafts formal bureaucratic dispatch emails to the responsible departments.

## ✨ Key Features

* **🗺️ Strategic Civic Radar:** A real-time Google Maps interface that geolocates issues and color-codes them by AI-determined severity.
* **🤖 Autonomous AI Dispatcher:** Users upload photos; Gemini 1.5 Flash instantly analyzes the image to categorize the damage and assign a 1-10 severity score without manual data entry.
* **📍 Smart Spatial Deduplication:** Calculates Haversine distances to prevent duplicate reports. Issues within a 20m radius are aggregated as "Community Validations" (upvotes).
* **✉️ Agentic Bureaucratic Routing:** Autonomously drafts and dispatches formal, legally structured emails to municipal departments containing exact GPS coordinates and AI assessments.
* **🔄 Closed-Loop Verification:** A transparent 5-step pipeline tracking issues from "Reported" to "Verified." Citizens must physically verify a repair before a ticket is officially closed.

## 🛠️ Technology Stack

* **Frontend:** HTML5, CSS3, Vanilla JavaScript (Dynamic Light/Dark Themes)
* **Backend:** Python 3.10, FastAPI, Uvicorn
* **Database:** SQLite
* **AI & Mapping:** Google Gemini 1.5 Flash, Google Maps JavaScript API
* **Deployment & DevOps:** Docker, Google Cloud Run, Google Cloud Build

---

## 🧪 Testing the Application (For Judges)

The application features a Dual-Role Operations Console. Use the following credentials to explore both sides of the platform.

### Citizen Portal
* **Username:** `citizen`
* **Password:** `admin`
* **Capabilities:** View the radar map, report new infrastructure issues via photo upload, and track the live resolution feed.

### Department Operations Console
* **Username:** `dept`
* **Password:** `admin`
* **Capabilities:** Review autonomously routed tickets, view the actual Agentic AI-generated dispatch emails, and advance pipeline statuses.

---

## 💻 Local Development Setup

To run this project locally on your machine:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/CommunityCare-AI.git](https://github.com/YOUR_USERNAME/CommunityCare-AI.git)
   cd CommunityCare-AI
Install dependencies:

Bash
pip install -r requirements.txt
Set Environment Variables:
You must provide a valid Gmail App Password to enable the agentic email dispatcher.

Linux/macOS: export GMAIL_APP_PASSWORD="your_app_password"

Windows (PowerShell): $env:GMAIL_APP_PASSWORD="your_app_password"

Run the FastAPI server:

Bash
uvicorn main:app --reload
Access the app: Open http://127.0.0.1:8000 in your browser.
