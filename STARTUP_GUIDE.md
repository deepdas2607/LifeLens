# 🚀 LifeLens - Demo Startup Guide

## Quick Start for Judges

This guide will help you run the complete LifeLens system for evaluation.

---

## 📋 Prerequisites

Ensure these are installed:
- ✅ Python 3.8+ (dependencies are auto-installed on first run)
- ✅ Modern web browser (Chrome/Edge recommended)
- ✅ Internet connection (for Qdrant Cloud & AI APIs)

Before first run:
- Copy `.env.example` to `.env`
- Add your `GROQ_API_KEY`, `GEMINI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY`

---

## 🎬 Option 1: One-Click Demo (Recommended)

### Start Everything at Once

```bash
start_complete_demo.bat
```

This launches all services:
- ✅ API Server (port 8000)
- ✅ Streamlit App (port 8501)  
- ✅ Medication Scheduler (background notifications)

The launcher also bootstraps `.venv` and installs dependencies automatically on first run.

---

## 🎬 Option 2: Manual Startup (Step by Step)

### Step 1: Start API Server (For Browser Extension)

```bash
start_api_server.bat
```

**What it does:**
- Starts FastAPI server on `http://localhost:8000`
- Handles browser extension requests
- Saves memories to Qdrant

**Wait for:** `Uvicorn running on http://0.0.0.0:8000`

---

### Step 2: Start Streamlit App (Main Dashboard)

```bash
start_lifelens.bat
```

**What it does:**
- Opens main LifeLens dashboard at `http://localhost:8501`
- Patient/Caretaker/Family portal
- Memory upload, search, medications, mood tracking

**Wait for:** Browser opens automatically

---

### Step 3: Start Medication Scheduler (Optional - For Notifications)

```bash
start_medication_scheduler.bat
```

**What it does:**
- Checks for upcoming medication reminders every minute
- Monitors missed doses
- Sends ntfy.sh notifications
- Runs nightly adherence analytics

**To test notifications:** Add medications in the Medications page and wait for scheduled times

---

## 🧩 Browser Extension Setup

### Load the Extension

1. Open Chrome/Edge
2. Navigate to `chrome://extensions`
3. Enable **Developer Mode** (toggle in top-right)
4. Click **Load unpacked**
5. Select folder: `lifelens/extension`

### Login to Extension

- Username: `patient1`
- Password: `patient123`

### Test Extension Features

1. **Save Selected Text:**
   - Highlight any text on a webpage
   - Right-click → "Save selection to LifeLens"
   - Check for "OK" badge

2. **Save Quick Note:**
   - Click extension icon
   - Write in text area
   - Click "Save Memory"

3. **View Memory Lane:**
   - Click extension icon
   - Switch to "Memory Lane" tab
   - See your saved memories

---

## 👥 Demo Accounts

### Patient Account (Full Access)
- Username: `patient1`
- Password: `patient123`
- Can use: App + Extension

### Caretaker Account (Monitor & Manage)
- Username: `caretaker1`
- Password: `care123`
- Can use: App only (view patient data)

### Family Account (View Only)
- Username: `family1`
- Password: `family123`
- Can use: App only (view memories)

---

## 🎯 Demo Flow for Judges

### 1. Show Multi-Modal Memory Capture (5 min)

**In Streamlit App:**
- Login as `patient1`
- Upload an image (Dashboard → Image section)
- Upload an audio file (Dashboard → Audio section)
- Add a text memory (Dashboard → Text section)

**In Browser Extension:**
- Open any webpage
- Select interesting text → Right-click → Save to LifeLens
- Open extension popup → Add a quick note

### 2. Show Semantic Search (2 min)

- Go to Dashboard
- Use search bar: "What did I do yesterday?"
- Show memories retrieved with similarity scores
- Try different queries to demonstrate semantic understanding

### 3. Show Medication Management (3 min)

- Navigate to Medications page
- View existing medications
- Show adherence calendar
- Show analytics and insights
- Point out missed doses tracking

### 4. Show Mood Tracking (3 min)

- Navigate to Mood Tracking page
- View mood timeline and patterns
- Show risk alerts (if any)
- Demonstrate trend analysis

### 5. Show Family Portal (2 min)

- Logout from patient1
- Login as `family1`
- Show read-only access to memories
- Demonstrate safe viewing without editing

### 6. Show Real-Time Notifications (2 min)

**If medication scheduler is running:**
- Open https://ntfy.sh/lifelens-caregiver-alerts
- Show push notifications for:
  - Upcoming medication reminders
  - Missed doses
  - Mood risk alerts

---

## 🔍 Key Features to Highlight

### ✅ Multi-Agent Architecture
- Planner, Critic, Executor agents working in coordination
- Quality control through critic feedback loops
- Demonstrated in mood analysis and medication insights

### ✅ Vector Search with Qdrant
- Semantic similarity search using Gemini embeddings
- 3072-dimension vectors
- Fast retrieval with metadata filtering

### ✅ Real-Time Intelligence
- Medication adherence monitoring
- Mood risk detection with multi-signal analysis
- Automated insights generation

### ✅ Privacy & Security
- Role-based access control (Patient/Caretaker/Family)
- JWT authentication
- SHA-256 password hashing
- Patient data isolation

### ✅ Cross-Platform Integration
- Web dashboard (Streamlit)
- Browser extension (Manifest V3)
- API-first architecture (RESTful)
- Mobile-ready notifications (ntfy.sh)

---

## 📊 System Architecture

```
┌─────────────────────┐        ┌─────────────────────┐
│  Browser Extension  │───────▶│   FastAPI Server    │
│   (Manifest V3)     │        │    (port 8000)       │
└─────────────────────┘        └──────────┬──────────┘
                                          │
┌─────────────────────┐                   │
│   Streamlit App     │                   │
│    (port 8501)      │───────────────────┤
└─────────────────────┘                   │
                                          ▼
┌─────────────────────┐        ┌─────────────────────┐
│ Medication Service  │───────▶│   Qdrant Cloud      │
│   (Background)      │        │  (Vector Database)   │
└─────────────────────┘        └──────────┬──────────┘
                                          │
                               ┌──────────▼──────────┐
                               │    AI Models        │
                               │  - Gemini (LLM)     │
                               │  - Groq (Audio)     │
                               │  - Vision (Images)  │
                               └─────────────────────┘
```

---

## 🛠 Troubleshooting

### API Server won't start
- Check if port 8000 is already in use
- Verify `.env` file exists with proper credentials

### Streamlit app shows errors
- Ensure all dependencies installed: `pip install -r lifelens/requirements.txt`
- Check `.env` has valid API keys

### Extension not saving data
- Verify API server is running at http://localhost:8000
- Check browser console (F12) for errors
- Ensure logged in as patient account

### No notifications appearing
- Verify medication scheduler is running
- Add a medication with upcoming dose time
- Check https://ntfy.sh/lifelens-caregiver-alerts

---

## 🎓 Evaluation Checklist

- [ ] API Server started (port 8000)
- [ ] Streamlit App opened (port 8501)
- [ ] Browser extension loaded
- [ ] Logged into extension as patient1
- [ ] Uploaded image memory
- [ ] Uploaded audio memory
- [ ] Saved text memory via extension
- [ ] Performed semantic search
- [ ] Viewed medication tracking
- [ ] Checked mood analysis
- [ ] Tested family portal access
- [ ] Demonstrated notification system

---

## 📞 Services Overview

| Service | Port | Status Check | Purpose |
|---------|------|--------------|---------|
| **API Server** | 8000 | http://localhost:8000/ | Extension backend |
| **Streamlit** | 8501 | http://localhost:8501/ | Main dashboard |
| **Qdrant** | 6333 | Cloud-hosted | Vector database |
| **Medication Scheduler** | - | Background service | Notifications |

---

## 🏁 Shutdown Services

**To stop all services:**
- Close all terminal windows
- Or press `Ctrl+C` in each terminal

**To restart:**
- Run `start_complete_demo.bat` again

---

<div align="center">

### 🧠 LifeLens - AI-Powered Memory Companion for Dementia Care

**Built with Gemini, Groq, Qdrant, Streamlit**

</div>
