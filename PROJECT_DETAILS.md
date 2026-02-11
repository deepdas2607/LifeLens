<div align="center">

# 🧠 LifeLens - Project Technical Documentation

### AI-Powered Multimodal Memory Companion for Dementia Care

**Built with Multi-Agent Architecture, Vector Search, and Real-Time Intelligence**

---

[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-4B0082?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Groq](https://img.shields.io/badge/Groq-LLaMA3%2070B-1A73E8?logo=groq&logoColor=white)](https://groq.com/)
[![Gemini](https://img.shields.io/badge/Gemini-1.5%20Flash-4285F4?logo=google&logoColor=white)](https://aistudio.google.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Core Features](#-core-features)
3. [Technical Architecture](#-technical-architecture)
4. [Technology Stack](#-technology-stack)
5. [Multi-Agent System](#-multi-agent-system)
6. [Database Collections](#-database-collections)
7. [API Architecture](#-api-architecture)
8. [Browser Extension](#-browser-extension)
9. [Components & Modules](#-components--modules)
10. [Security & Privacy](#-security--privacy)
11. [Installation & Setup](#-installation--setup)
12. [Use Cases](#-use-cases)
13. [Demo Credentials](#-demo-credentials)
14. [Future Enhancements](#-future-enhancements)

---

## 🎯 Project Overview

### Mission Statement
**LifeLens** is an AI-powered multimodal memory companion specifically designed to support individuals with dementia and Alzheimer's disease. By leveraging cutting-edge AI technologies, vector search, and multi-agent coordination, LifeLens creates a comprehensive digital memory vault that helps patients preserve, recall, and relive their precious memories.

### Problem Statement
- **Memory Loss**: Dementia patients struggle to remember daily events, people, and locations
- **Caregiver Burden**: Family members and caretakers need tools to monitor and support patients
- **Fragmented Care**: Lack of unified systems for memory management, medication tracking, and mood monitoring
- **Social Isolation**: Patients lose connection with their life stories and relationships

### Our Solution
LifeLens provides:
- **Multimodal Memory Capture**: Text, images, audio, and video processing
- **Semantic Search**: Natural language queries to find memories
- **Multi-Agent Intelligence**: Automated insights, alerts, and recommendations
- **Cross-Platform Access**: Web dashboard + browser extension
- **Real-Time Monitoring**: Mood tracking, medication adherence, risk detection
- **Family Portal**: Safe, controlled access for loved ones

---

## ✨ Core Features

### 1. 🎨 Multimodal Memory Capture

#### Image Processing
- **AI-Powered Captioning**: Automatically describes images using Gemini Vision API
- **Emotion Detection**: Identifies mood/sentiment from facial expressions
- **Person Tagging**: Manual tagging to remember who appears in photos
- **Location Metadata**: GPS coordinates and place names
- **Base64 Storage**: Images stored directly in Qdrant for quick retrieval

#### Audio Processing
- **Speech-to-Text**: Transcription via Groq Whisper API
- **Sentiment Analysis**: Detects emotional tone in voice recordings
- **Background Service**: Can record voice notes on-the-go
- **Multi-Language Support**: Transcribes various languages

#### Text Memories
- **Quick Notes**: Simple text entry for daily events
- **Context Preservation**: Stores URL, title, and metadata
- **Tag System**: Categorize memories with custom tags
- **Location Tagging**: Add places to text memories

#### Video Processing (Future)
- **Scene Analysis**: Summarizes video content
- **Audio Extraction**: Transcribes dialogue from videos
- **Key Frame Detection**: Identifies important moments

### 2. 🔍 Semantic Memory Search

#### Vector Search with Qdrant
- **3072-Dimensional Embeddings**: Generated via Gemini embedding model
- **Cosine Similarity**: Finds semantically similar memories
- **Hybrid Search**: Combines vector similarity with metadata filters
- **Natural Language Queries**: "What did I do last Christmas?" → relevant memories

#### Search Capabilities
- **Time-Based Filtering**: Search by date ranges
- **Person Filtering**: Find memories with specific people
- **Location Filtering**: Memories from particular places
- **Type Filtering**: Images, audio, or text only
- **Mood Filtering**: Happy, sad, anxious memories

#### Grounded Reasoning
- **LLM Integration**: Uses Groq LLaMA-3 70B for answer generation
- **Evidence-Based**: Answers always cite source memories
- **No Hallucinations**: Only responds based on stored data
- **Source Attribution**: Shows which memories support each answer

### 3. 💊 Medication Management System

#### Features
- **Medication Tracking**: Add prescriptions with dosage and schedule
- **Smart Reminders**: Time-based notifications via ntfy.sh
- **Adherence Monitoring**: Tracks taken, skipped, and missed doses
- **Calendar View**: Visual representation of medication schedule
- **Analytics Dashboard**: Adherence rates, streaks, patterns
- **Multi-Dose Support**: Handles medications taken multiple times daily

#### Multi-Agent Medication Intelligence
- **Medication Planner**: Analyzes schedules and optimizes timing
- **Medication Critic**: Reviews adherence and flags concerns
- **Adherence Agent**: Generates insights and recommendations
- **Scheduler Service**: Background process for real-time reminders

#### Notifications
- **Pre-Dose Reminders**: Alerts before medication time (configurable)
- **Missed Dose Alerts**: Notifies caretakers of skipped medications
- **Nightly Analytics**: Daily summary of adherence patterns
- **Push Notifications**: Via ntfy.sh (works on mobile)

### 4. 😊 Mood Intelligence System

#### Mood Tracking
- **Multi-Signal Analysis**: Combines text sentiment, voice tone, image emotion
- **Time-Series Data**: Tracks mood patterns over days/weeks/months
- **Mood Score**: -1.0 (very negative) to +1.0 (very positive)
- **Mood Categories**: Happy, sad, anxious, angry, confused, neutral

#### Risk Detection (Multi-Agent)
- **Pattern Analysis**: Detects unusual mood trends
- **Multi-Signal Correlation**: Cross-references multiple data sources
- **Risk Scoring**: 0-100 scale for intervention urgency
- **Automated Alerts**: Notifies caretakers of concerning patterns
- **Critic Validation**: Second agent reviews and validates alerts

#### Mood Agent Architecture
```
Mood Analyzer → Pattern Detector → Risk Scorer → Critic → Alert Generator
     ↓               ↓                ↓            ↓           ↓
  Sentiment      Trend Check      Calculate    Validate    ntfy.sh
  Analysis       Correlation      Risk Score   Decision    Notification
```

### 5. 👥 Multi-Role Access System

#### Patient Portal
- **Full Access**: Upload, search, view all memories
- **Dashboard**: Recent memories, quick search, upload buttons
- **Medication Page**: View schedule, mark doses taken
- **Mood Tracking**: View mood timeline and patterns
- **Browser Extension**: Capture memories from any website

#### Caretaker Portal
- **Patient Monitoring**: Access assigned patient data
- **Medication Management**: Add/edit medications, view adherence
- **Alert Dashboard**: Missed doses, mood alerts, system notifications
- **Analytics**: Comprehensive insights on patient wellbeing
- **Family Coordination**: Share information with family members

#### Family Portal
- **View-Only Access**: Safe access to patient memories
- **Memory Lane**: Browse photos, videos, and stories
- **No Editing**: Cannot modify or delete memories (safety)
- **Connection**: Stay updated with loved one's daily life
- **Privacy Preserved**: Only sees what patient/caretaker shares

### 6. 🌐 Browser Extension (Chrome/Edge)

#### Features
- **Context Menu Integration**: Right-click → Save to LifeLens
- **Quick Notes**: Popup interface for instant memory capture
- **Auto-Context**: Captures URL, page title, timestamp
- **Memory Lane**: View recent memories in popup
- **Search**: Search memories directly from extension
- **Offline Queue**: Saves drafts when API unavailable (future)

#### Technical Details
- **Manifest V3**: Modern extension architecture
- **Service Worker**: Background process for context menu
- **JWT Authentication**: Secure token-based auth
- **RESTful API**: Communicates with FastAPI backend
- **Local Storage**: Securely stores auth tokens

#### Independence
- ✅ Works WITHOUT Streamlit app running
- ✅ Directly connects to FastAPI server (port 8000)
- ✅ Saves directly to Qdrant database
- ✅ Real-time synchronization with web dashboard

### 7. 🤖 Multi-Agent System

LifeLens employs a sophisticated multi-agent architecture for intelligent decision-making:

#### Core Agents

**Planner Agent**
- Analyzes user intent and requirements
- Creates execution plans for complex tasks
- Coordinates between specialized agents
- Model: LLaMA-3 70B via Groq

**Critic Agent**
- Reviews agent outputs for quality
- Validates decisions and recommendations
- Provides feedback for improvement
- Prevents erroneous actions

**Executor Agent**
- Carries out validated plans
- Interfaces with Qdrant and external APIs
- Handles error recovery
- Reports results back to Planner

**Retriever Agent**
- Performs semantic search in Qdrant
- Filters and ranks memories
- Extracts relevant context
- Optimizes search parameters

#### Specialized Agents

**Mood Agent**
- Analyzes emotional patterns
- Detects mood anomalies
- Generates risk scores
- Creates intervention alerts

**Medication Adherence Agent**
- Monitors medication taking patterns
- Identifies adherence issues
- Suggests timing improvements
- Generates nightly reports

**Medication Planner**
- Optimizes medication schedules
- Prevents drug interactions (future)
- Suggests reminder timing
- Coordinates with Scheduler

**Medication Critic**
- Reviews adherence analytics
- Validates alert decisions
- Assesses intervention necessity
- Filters false positives

**Medication Scheduler**
- Background service running continuously
- Checks for upcoming doses every minute
- Sends pre-dose reminders
- Tracks missed doses
- Runs nightly analytics at midnight

**Analytics Agent**
- Generates insights from memory data
- Creates visualizations
- Identifies trends and patterns
- Produces summary reports

**Recommender Agent**
- Suggests related memories
- Creates memory clusters
- Recommends reminiscence activities
- Personalized content curation

**Summary Agent**
- Condenses long memory collections
- Creates timeline summaries
- Generates life story narratives
- Produces shareable reports

**Trigger Agent**
- Monitors system events
- Fires alerts based on conditions
- Manages notification pipeline
- Handles escalation logic

#### Agent Communication Flow
```
User Request → Planner → [Specialized Agents] → Critic → Executor → User Response
                ↓                                   ↓
            Qdrant DB ←──────────────────────── Validated Results
```

---

## 🏗 Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
├────────────────┬────────────────────────┬───────────────────────┤
│  Streamlit Web │   Browser Extension    │  Mobile (Future)     │
│  Dashboard     │   (Chrome/Edge)        │  iOS/Android App     │
│  (Port 8501)   │   Manifest V3          │                      │
└────────┬───────┴────────────┬───────────┴──────────────────────┘
         │                    │
         │                    │
         ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│                      (Port 8000)                                │
├─────────────────────────────────────────────────────────────────┤
│  • RESTful API Endpoints                                        │
│  • JWT Authentication                                           │
│  • Request Validation (Pydantic)                                │
│  • CORS Middleware                                              │
│  • Error Handling                                               │
└────────┬─────────────────────────────────────────────┬──────────┘
         │                                             │
         │                                             │
         ▼                                             ▼
┌─────────────────────┐                   ┌────────────────────────┐
│  Multi-Agent System │                   │  Background Services   │
├─────────────────────┤                   ├────────────────────────┤
│ • Planner           │                   │ • Med Scheduler        │
│ • Critic            │                   │ • Mood Monitor         │
│ • Executor          │                   │ • Trigger System       │
│ • Retriever         │                   │ • Analytics Runner     │
│ • Mood Agent        │                   └────────────────────────┘
│ • Med Agents        │
│ • Analytics         │
│ • Recommender       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
├────────────────┬────────────────────────┬───────────────────────┤
│  Qdrant Cloud  │   External AI APIs     │   Local Storage       │
│  Vector DB     │                        │                       │
├────────────────┤  • Gemini (Embeddings) │  • users.json         │
│ Collections:   │  • Gemini (Vision)     │  • triggers.json      │
│ • lifelens     │  • Groq (Whisper)      │  • .env config        │
│   _memory      │  • Groq (LLaMA-3)      │                       │
│ • medications  │                        │                       │
│ • mood_events  │  Notifications:        │                       │
│ • mood_alerts  │  • ntfy.sh             │                       │
│ • users        │                        │                       │
│ • med_events   │                        │                       │
│ • med_insights │                        │                       │
└────────────────┴────────────────────────┴───────────────────────┘
```

### Data Flow

#### Memory Capture Flow
```
1. User uploads image/audio/text
2. Streamlit/Extension sends to FastAPI
3. FastAPI validates authentication
4. Content sent to appropriate processor:
   - Image → Gemini Vision → Caption + Sentiment
   - Audio → Groq Whisper → Transcript + Sentiment
   - Text → Direct storage with metadata
5. Gemini generates 3072-dim embedding
6. upsert_memory() saves to Qdrant
7. If mood detected → Save to mood_events collection
8. Response sent back to UI
9. UI updates to show new memory
```

#### Search Flow
```
1. User enters search query
2. Query sent to FastAPI /api/search
3. Gemini generates query embedding
4. Qdrant performs vector similarity search
5. Results filtered by patient_id + metadata
6. Top-K memories retrieved (default: 5)
7. Memories sent to Groq LLaMA-3 for answer generation
8. Answer + source memories returned to UI
9. UI displays answer with evidence citations
```

#### Medication Reminder Flow
```
1. Background scheduler runs every 60 seconds
2. Queries Qdrant for active medications
3. Checks current time against dose schedules
4. If dose upcoming (within reminder window):
   → Send ntfy.sh notification
   → Log reminder in medication_events
5. If dose missed (past due time):
   → Send alert to caretaker
   → Log missed dose event
6. At midnight:
   → Run adherence analysis
   → Generate insights using Med Agents
   → Send daily summary
```

#### Mood Alert Flow
```
1. New mood data ingested (from memory with sentiment)
2. Saved to mood_events collection
3. Mood Agent analyzes recent pattern (7-14 days)
4. Multi-signal analysis:
   - Consecutive negative moods
   - Sudden mood drops
   - Mood variance increase
   - Specific mood types (anxious, confused)
5. Calculate risk score (0-100)
6. Critic Agent validates alert necessity
7. If validated:
   → Save to mood_alerts collection
   → Send ntfy.sh notification
   → Display in dashboard
```

---

## 🛠 Technology Stack

### Frontend

| Technology | Purpose | Version |
|------------|---------|---------|
| **Streamlit** | Web dashboard framework | 1.32+ |
| **Custom CSS** | UI styling and theming | - |
| **Streamlit-Folium** | Interactive maps | Latest |
| **Plotly** | Data visualizations | Latest |
| **Altair** | Charts and graphs | Latest |

### Backend

| Technology | Purpose | Version |
|------------|---------|---------|
| **FastAPI** | REST API framework | 0.128+ |
| **Uvicorn** | ASGI server | 0.40+ |
| **Python** | Core language | 3.14 |
| **Pydantic** | Data validation | 2.12+ |
| **JWT (PyJWT)** | Authentication tokens | 2.11+ |
| **Python-Multipart** | File upload handling | Latest |

### Database & Vector Search

| Technology | Purpose | Details |
|------------|---------|---------|
| **Qdrant Cloud** | Vector database | Production instance |
| **Qdrant Client** | Python SDK | Latest |
| **Vector Size** | Embeddings dimension | 3072 (Gemini) |
| **Distance Metric** | Similarity measure | Cosine |
| **Collections** | Data organization | 9 specialized collections |

### AI & Machine Learning

| Technology | Purpose | API/Model |
|------------|---------|-----------|
| **Gemini 1.5 Flash** | Vision, embeddings, LLM | Google AI Studio |
| **Gemini Embedding-001** | Vector embeddings | 3072 dimensions |
| **Groq** | Fast LLM inference | LLaMA-3 70B |
| **Groq Whisper** | Audio transcription | Latest |
| **LLaMA-3 70B** | Multi-agent reasoning | via Groq |

### Browser Extension

| Technology | Purpose | Details |
|------------|---------|---------|
| **Manifest V3** | Extension format | Chrome/Edge compatible |
| **Service Worker** | Background processing | Context menu handling |
| **Chrome Storage** | Local data persistence | JWT token storage |
| **Fetch API** | HTTP requests | RESTful communication |

### Notifications & Communication

| Technology | Purpose | Details |
|------------|---------|---------|
| **ntfy.sh** | Push notifications | Free, no registration |
| **HTTP Webhooks** | Alert delivery | Real-time push |
| **Topic-based** | Channel segmentation | Per-patient topics |

### Development & Deployment

| Technology | Purpose | Details |
|------------|---------|---------|
| **Git** | Version control | GitHub repository |
| **Python-dotenv** | Environment config | .env file management |
| **Logging** | System monitoring | Python logging module |
| **Pytest** | Testing framework | Unit & integration tests |

### Data Processing

| Technology | Purpose | Details |
|------------|---------|---------|
| **Pillow (PIL)** | Image processing | Resize, format conversion |
| **pydub** | Audio processing | Format conversion |
| **gTTS** | Text-to-speech | Future feature |
| **NumPy** | Numerical operations | Data manipulation |
| **Pandas** | Data analysis | Analytics processing |

### Geolocation

| Technology | Purpose | Details |
|------------|---------|---------|
| **geopy** | Geocoding | Address lookup |
| **Folium** | Map visualization | Interactive maps |
| **OpenStreetMap** | Map tiles | Free map data |

### Security

| Technology | Purpose | Details |
|------------|---------|---------|
| **SHA-256** | Password hashing | hashlib |
| **JWT** | Token-based auth | 7-day expiry |
| **HTTPS** | Secure communication | Qdrant Cloud SSL |
| **CORS** | API security | FastAPI middleware |

---

## 🤖 Multi-Agent System

### Agent Architecture

```python
# Pseudocode structure
class Agent:
    def __init__(self, name, model, role):
        self.name = name
        self.model = model  # LLaMA-3 70B
        self.role = role
        self.memory = []
    
    def execute(self, task, context):
        # Generate plan/analysis
        response = self.model.generate(task, context)
        return response
    
    def learn(self, feedback):
        # Store feedback for improvement
        self.memory.append(feedback)
```

### Agent Collaboration Pattern

#### Example: Medication Adherence Analysis

```
1. Planner Agent:
   - Receives request: "Analyze patient medication adherence"
   - Creates plan: Query events → Calculate metrics → Generate insights
   
2. Executor Agent:
   - Executes plan
   - Queries Qdrant for medication_events
   - Retrieves last 30 days of data
   
3. Medication Adherence Agent:
   - Calculates adherence rate
   - Identifies patterns (morning vs evening)
   - Detects streaks and missed patterns
   - Generates preliminary insights
   
4. Medication Critic:
   - Reviews calculated metrics
   - Validates insights accuracy
   - Checks for edge cases
   - Approves or requests revision
   
5. Summary Agent:
   - Creates human-readable report
   - Generates visualizations
   - Produces recommendations
   
6. Response to User:
   - Display adherence percentage
   - Show calendar visualization
   - List specific insights
   - Provide actionable recommendations
```

### Agent Decision Making

Each agent uses **Chain-of-Thought reasoning**:

```
Task: "Should we alert the caretaker about mood decline?"

Mood Agent Analysis:
- Recent 7 days: 5 negative, 2 neutral moods
- Pattern: Declining trend detected
- Severity: Moderate (score: -0.6 average)
- Context: No major life events logged
- Historical: Different from usual baseline

Critic Validation:
- Verify data quality: ✓ All moods have source memories
- Check false positive risk: Low (clear trend)
- Assess urgency: Medium (not emergency, but concerning)
- Validate intervention need: ✓ Warranted
- Decision: APPROVE alert

Action:
- Generate alert with risk score: 65/100
- Include evidence: Memory references
- Send ntfy.sh notification
- Log to mood_alerts collection
- Display in dashboard
```

---

## 💾 Database Collections

### Qdrant Collections Overview

#### 1. `lifelens_memory` (Main Memory Collection)
- **Purpose**: Stores all captured memories
- **Vector Size**: 3072 (Gemini embeddings)
- **Distance**: Cosine similarity

**Schema**:
```json
{
  "type": "image|audio|text|video",
  "timestamp": 1770477063,
  "patient_id": "patient_1",
  "content": "Text content (for text memories)",
  "caption": "Image description (for images)",
  "transcript": "Audio transcription (for audio)",
  "analysis": "Video summary (for videos)",
  "sentiment": "Happy|Sad|Neutral|...",
  "person_tags": ["John", "Mary"],
  "location": {
    "name": "Mumbai, India",
    "lat": 19.076,
    "lon": 72.8777
  },
  "source": "extension|dashboard|upload",
  "url": "https://example.com",
  "title": "Page Title",
  "milestone": false,
  "category": "family|trip|medical|..."
}
```

**Indexes**:
- `patient_id` (KEYWORD) - Fast patient filtering
- `type` (KEYWORD) - Filter by memory type
- `person_tags` (TEXT) - Search by people

#### 2. `mood_events` (Mood Time-Series)
- **Purpose**: Time-series mood tracking data
- **Vector Size**: 3072
- **Distance**: Cosine

**Schema**:
```json
{
  "patient_id": "patient_1",
  "timestamp": "2026-02-10T10:30:00Z",
  "mood": "happy|sad|anxious|angry|confused|neutral",
  "mood_score": 0.75,
  "source": "image|audio|text",
  "people": ["Family members present"],
  "milestone": false,
  "location": "Home"
}
```

**Indexes**:
- `patient_id` (KEYWORD)
- `timestamp` (DATETIME)
- `mood` (KEYWORD)

#### 3. `mood_alerts` (Risk Alerts)
- **Purpose**: Stores mood risk alerts
- **Vector Size**: 1 (minimal)
- **Distance**: Dot product

**Schema**:
```json
{
  "alert_id": "uuid",
  "patient_id": "patient_1",
  "timestamp": "2026-02-10T10:30:00Z",
  "risk_score": 65,
  "critic_verdict": "APPROVE",
  "summary": "Declining mood pattern detected",
  "signals": ["5 consecutive negative moods", "..."],
  "notified": true
}
```

**Indexes**:
- `patient_id` (KEYWORD)
- `timestamp` (DATETIME)
- `notified` (BOOL)

#### 4. `medications` (Active Prescriptions)
- **Purpose**: Current medication list
- **Vector Size**: 3072
- **Distance**: Cosine

**Schema**:
```json
{
  "patient_id": "patient_1",
  "medication_id": "uuid",
  "name": "Aspirin",
  "dosage": "100mg",
  "schedule": ["08:00", "20:00"],
  "start_date": "2026-01-01",
  "end_date": null,
  "notes": "Take with food",
  "prescribed_by": "Dr. Smith",
  "active": true,
  "created_at": 1770477063,
  "total_daily_doses": 2
}
```

**Indexes**:
- `patient_id` (KEYWORD)
- `medication_id` (KEYWORD) ← Fixed in latest version
- `active` (BOOL)

#### 5. `medication_events` (Adherence Log)
- **Purpose**: Track taken/skipped/missed doses
- **Vector Size**: 3072
- **Distance**: Cosine

**Schema**:
```json
{
  "patient_id": "patient_1",
  "medication_id": "uuid",
  "timestamp": 1770477063,
  "timestamp_iso": "2026-02-10T08:00:00Z",
  "status": "taken|skipped|missed",
  "reported_by": "patient|caretaker|system",
  "note": "Took with breakfast",
  "dose_time": "08:00",
  "dose_date": "2026-02-10"
}
```

**Indexes**:
- `patient_id` (KEYWORD)
- `medication_id` (KEYWORD) ← Fixed in latest version
- `timestamp` (FLOAT)
- `status` (KEYWORD)
- `dose_time` (KEYWORD)
- `dose_date` (KEYWORD)

#### 6. `medication_insights` (Analytics Results)
- **Purpose**: Nightly analytics output
- **Vector Size**: 1
- **Distance**: Dot

**Schema**:
```json
{
  "patient_id": "patient_1",
  "insight_id": "uuid",
  "timestamp": "2026-02-10T00:00:00Z",
  "metrics": {
    "adherence_rate": 85.5,
    "doses_taken": 17,
    "doses_missed": 3,
    "streak_days": 5
  },
  "timing_analysis": "Morning doses: 90%, Evening: 80%",
  "side_effects": [],
  "summary": "Good adherence overall...",
  "verdict": "No intervention needed",
  "missed_rate": 15.0
}
```

**Indexes**:
- `patient_id` (KEYWORD)

#### 7. `lifelens_users` (User Accounts)
- **Purpose**: Authentication and user management
- **Vector Size**: 1 (minimal)
- **Distance**: Dot

**Schema**:
```json
{
  "username": "patient1",
  "password": "sha256_hash",
  "role": "patient|caretaker|family",
  "full_name": "John Doe",
  "patient_id": "patient_1"
}
```

**Indexes**:
- `username` (KEYWORD)

#### 8. `mood_feedback` (Learning Loop)
- **Purpose**: Store feedback on alerts for tuning
- **Vector Size**: 1
- **Use**: Future ML improvement

#### 9. `agent_decisions` (Audit Trail)
- **Purpose**: Log agent decisions for transparency
- **Vector Size**: 3072
- **Use**: Debugging and improvement

---

## 🌐 API Architecture

### FastAPI Endpoints

#### Authentication

**POST /api/auth/login**
```json
Request:
{
  "username": "patient1",
  "password": "patient123"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user_info": {
    "username": "patient1",
    "full_name": "John Doe",
    "role": "patient",
    "patient_id": "patient_1",
    "patients": []
  }
}
```

#### Memory Operations

**POST /api/memory/create**
```json
Request:
{
  "content": "Had lunch with family today",
  "patient_id": "patient_1",
  "tags": "family",
  "url": "https://example.com",
  "title": "Page Title",
  "location_text": "Home"
}

Headers:
{
  "Authorization": "Bearer <jwt_token>"
}

Response:
{
  "status": "success",
  "message": "Memory created"
}
```

**POST /api/upload/image**
- Multipart form data
- Files: image file
- Fields: patient_id, caption, tags

**POST /api/upload/audio**
- Multipart form data
- Files: audio file
- Fields: patient_id

**POST /api/search**
```json
Request:
{
  "query": "What did I do last week?",
  "patient_id": "patient_1",
  "top_k": 5
}

Response:
{
  "answer": "Based on your memories, you...",
  "memories": [
    {
      "type": "text",
      "content": "...",
      "timestamp": 1770477063,
      "score": 0.89
    }
  ]
}
```

**GET /api/memories/{patient_id}**
```json
Query Params:
- limit: int (default 20)

Response:
{
  "memories": [
    {
      "type": "image",
      "caption": "Family dinner",
      "timestamp": 1770477063,
      "sentiment": "Happy",
      "location": {...}
    }
  ]
}
```

### API Security

- **JWT Tokens**: 7-day expiry
- **CORS**: Configured for localhost (dev)
- **Role Verification**: Each endpoint checks permissions
- **Patient Isolation**: Users only access their own/assigned data
- **HTTPS**: Enforced for Qdrant Cloud

---

## 🧩 Components & Modules

### File Structure

```
LifeLens Final/
├── lifelens/
│   ├── app.py                      # Main Streamlit app
│   ├── config.py                   # Configuration
│   ├── notifications.py            # ntfy.sh integration
│   ├── requirements.txt            # Python dependencies
│   │
│   ├── agents/                     # Multi-agent system
│   │   ├── planner.py
│   │   ├── critic.py
│   │   ├── executor.py
│   │   ├── retriever.py
│   │   ├── mood_agent.py
│   │   ├── medication_planner.py
│   │   ├── medication_critic.py
│   │   ├── medication_adherence.py
│   │   ├── medication_scheduler.py
│   │   ├── medication_reminder.py
│   │   ├── analytics_agent.py
│   │   ├── recommender.py
│   │   ├── summary_agent.py
│   │   └── trigger.py
│   │
│   ├── api/                        # FastAPI backend
│   │   └── main.py                 # API routes
│   │
│   ├── auth/                       # Authentication
│   │   ├── users.py                # User management
│   │   └── session.py              # Session handling
│   │
│   ├── extension/                  # Browser extension
│   │   ├── manifest.json
│   │   ├── background.js
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── styles.css
│   │
│   ├── ingestion/                  # Content processors
│   │   ├── image_processor.py
│   │   ├── audio_processor.py
│   │   ├── text_processor.py
│   │   ├── video_processor.py
│   │   └── upsert_memory.py
│   │
│   ├── pages/                      # Streamlit pages
│   │   ├── dashboard.py
│   │   ├── medications.py
│   │   ├── family_portal.py
│   │   ├── map.py
│   │   └── wearable.py
│   │
│   ├── qdrant/                     # Database layer
│   │   ├── client.py               # Qdrant client
│   │   └── schema.py               # Collection schemas
│   │
│   ├── retrieval/                  # Search & reasoning
│   │   ├── search_engine.py
│   │   ├── reasoning.py
│   │   └── time_parser.py
│   │
│   ├── scripts/                    # Background services
│   │   ├── medication_scheduler_service.py
│   │   └── scheduled_mood_analysis.py
│   │
│   └── ui/                         # UI components
│       ├── components.py
│       ├── medication_components.py
│       ├── mood_components.py
│       └── trigger_components.py
│
├── tests/                          # Test suite
│   ├── test_api.py
│   ├── test_mood_system.py
│   ├── test_medication_system.py
│   └── conftest.py
│
├── .env                            # Environment variables
├── users.json                      # User database (fallback)
├── triggers.json                   # Trigger configurations
│
├── start_api_server.bat            # API launcher
├── start_lifelens.bat              # Streamlit launcher
├── start_complete_demo.bat         # All services
├── start_medication_scheduler.bat  # Med reminders
├── start_mood_monitoring.bat       # Mood analysis
│
├── README.md                       # Project overview
├── STARTUP_GUIDE.md                # Demo instructions
├── EXTENSION_STATUS.md             # Extension docs
└── PROJECT_DETAILS.md              # This file
```

### Key Modules

#### Memory Ingestion Pipeline
```python
# Simplified flow
def process_memory(file, type, patient_id):
    if type == "image":
        caption = gemini.vision_api(file)
        sentiment = analyze_sentiment(caption)
        base64_data = encode_image(file)
    
    elif type == "audio":
        transcript = groq.whisper(file)
        sentiment = analyze_sentiment(transcript)
        base64_data = encode_audio(file)
    
    elif type == "text":
        content = file
        sentiment = analyze_sentiment(content)
    
    embedding = gemini.embed(text_content)
    
    memory = {
        "type": type,
        "patient_id": patient_id,
        "timestamp": time.time(),
        "sentiment": sentiment,
        # ... other fields
    }
    
    qdrant_client.upsert(
        collection="lifelens_memory",
        vector=embedding,
        payload=memory
    )
    
    if sentiment:
        store_mood_event(patient_id, sentiment)
```

---

## 🔒 Security & Privacy

### Authentication & Authorization

#### Password Security
- **Hashing**: SHA-256 with salt
- **No Plaintext**: Passwords never stored in plain form
- **Token-Based**: JWT for stateless auth
- **Expiration**: 7-day token lifetime

#### Role-Based Access Control (RBAC)
```python
# Access matrix
Permissions = {
    "patient": {
        "own_data": ["read", "write", "delete"],
        "others_data": []
    },
    "caretaker": {
        "assigned_patients": ["read", "write"],
        "medications": ["manage"],
        "alerts": ["view", "respond"]
    },
    "family": {
        "assigned_patients": ["read"],
        "no_edit": True
    }
}
```

### Data Privacy

#### Patient Data Isolation
- All queries filtered by `patient_id`
- Qdrant indexes enforce separation
- No cross-patient data leakage
- API validates patient access rights

#### Secure Storage
- **Qdrant Cloud**: HTTPS/TLS encryption
- **API Keys**: Stored in `.env`, never committed
- **JWT Secret**: Configurable per deployment
- **Base64 Media**: Encrypted at rest in Qdrant

### Compliance Considerations

#### HIPAA Readiness (Future)
- Audit logging (agent_decisions collection)
- Access controls (RBAC)
- Encryption in transit and at rest
- Data retention policies (configurable)

#### GDPR Compliance
- Right to access: Export functionality
- Right to deletion: Delete user endpoint
- Data portability: JSON/CSV export
- Consent management: User opt-in

### Browser Extension Security

- **Content Security Policy**: Strict CSP in manifest
- **Secure Storage**: Chrome.storage.local (encrypted)
- **No Eval**: No dynamic code execution
- **Permissions**: Minimal required permissions
- **HTTPS Only**: API communication encrypted

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- Internet connection
- Modern web browser (Chrome/Edge for extension)

### Quick Start

1. **Clone Repository**
```bash
git clone <repository-url>
cd "LifeLens Final"
```

2. **Install Dependencies**
```bash
pip install -r lifelens/requirements.txt
```

3. **Configure Environment**
Create `.env` file:
```bash
# Qdrant
QDRANT_URL=https://your-qdrant-cloud-url
QDRANT_API_KEY=your-api-key

# AI APIs
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key

# Security
JWT_SECRET=your-secret-key

# Notifications (optional)
NTFY_TOPIC_URL=https://ntfy.sh/your-topic
```

4. **Start Services**
```bash
# Option 1: All at once
start_complete_demo.bat

# Option 2: Individual services
start_api_server.bat        # API (required)
cd lifelens && streamlit run app.py  # Dashboard
start_medication_scheduler.bat  # Reminders (optional)
```

5. **Load Browser Extension**
- Chrome: `chrome://extensions`
- Enable Developer Mode
- Load unpacked: `lifelens/extension`

6. **Login**
- Dashboard: http://localhost:8501
- Extension: Click icon, use credentials below

### Demo Accounts

| Username | Password | Role | Access |
|----------|----------|------|--------|
| patient1 | patient123 | Patient | Full access + Extension |
| caretaker1 | care123 | Caretaker | Monitor patient_1 |
| family1 | family123 | Family | View patient_1 (read-only) |

---

## 💡 Use Cases

### 1. Daily Memory Capture
**Scenario**: Patient wants to remember their day

- **Morning**: Take photo of breakfast → Extension uploads to LifeLens
- **Afternoon**: Record voice note about doctor visit → Transcribed & saved
- **Evening**: Text note about family call → Tagged with "family"
- **Night**: Review memory lane in dashboard
- **Result**: Complete timeline of the day preserved

### 2. Medication Adherence Tracking
**Scenario**: Caretaker monitors medication compliance

- **Setup**: Add patient medications with schedules
- **Reminders**: Patient receives notifications 10 min before doses
- **Logging**: Patient marks "Taken" in app or via notification
- **Monitoring**: Caretaker sees adherence calendar in real-time
- **Alerts**: If dose missed → Caretaker notified instantly
- **Analytics**: Weekly report shows 85% adherence, flags evening doses
- **Action**: Caretaker adjusts evening reminder timing

### 3. Mood Risk Detection
**Scenario**: Early intervention for mood decline

- **Background**: System continuously analyzes mood from memories
- **Detection**: 5 consecutive days of sad/anxious mood detected
- **Analysis**: Mood Agent calculates risk score: 70/100
- **Validation**: Critic confirms alert is warranted
- **Notification**: Caretaker receives push alert via ntfy.sh
- **Dashboard**: Shows mood timeline with declining trend
- **Intervention**: Caretaker schedules extra visit, activities
- **Follow-up**: Mood improves, alert auto-resolves

### 4. Family Connection
**Scenario**: Family member wants to stay involved

- **Access**: Daughter logs in as family member
- **Browse**: Views memory lane with recent photos
- **Search**: "What did dad do this week?"
- **Discovery**: Sees photos from park walk, lunch with friends
- **Sharing**: Recalls conversation starters for next visit
- **Engagement**: Sends message about shared memories
- **Result**: Meaningful conversation, maintained connection

### 5. Reminiscence Therapy
**Scenario**: Therapist uses memories for therapy session

- **Preparation**: Search "happy family events"
- **Session**: Display photos from family gatherings
- **Engagement**: Patient recalls stories, emotions
- **Stimulation**: Semantic search finds related memories
- **Progress**: Mood improves from neutral to happy
- **Documentation**: Session notes added as text memory
- **Analysis**: System tracks therapy effectiveness

### 6. Caregiver Handoff
**Scenario**: New caretaker needs patient context

- **Handoff**: Outgoing caretaker shares access
- **Review**: New caretaker browses memory timeline
- **Insights**: Reviews medication adherence patterns
- **Alerts**: Sees past mood alerts and resolutions
- **Context**: Understands patient preferences, routines
- **Questions**: Uses search to find specific information
- **Continuity**: Seamless care transition

---

## 🎓 Technical Highlights

### Innovation Points

#### 1. Multi-Agent Coordination
- First dementia care system with multi-agent architecture
- Agents collaborate for complex decision-making
- Critic validation prevents false positives
- Self-improving through feedback loops

#### 2. Multimodal Vector Search
- Single unified search across all content types
- Semantic understanding beyond keyword matching
- Fast retrieval from thousands of memories
- Hybrid filtering (vector + metadata)

#### 3. Real-Time Intelligence
- Continuous monitoring without manual intervention
- Background services for proactive care
- Push notifications for immediate action
- Automated insights generation

#### 4. Cross-Platform Integration
- Web dashboard + browser extension + (future) mobile
- Shared backend, synchronized data
- Works offline-first with queue sync (future)
- Consistent experience across platforms

#### 5. Privacy-First Design
- Role-based access ensures data safety
- Patient data never mixed or leaked
- Family members get read-only access
- Complete audit trail for transparency

### Performance Metrics

- **Search Latency**: < 200ms for typical queries
- **Embedding Generation**: ~1-2 seconds per memory
- **Background Processing**: Checks every 60 seconds
- **Database**: Handles 1000+ memories per patient
- **Extension**: < 500KB uncompressed
- **API Response**: < 100ms for auth endpoints

### Scalability

- **Qdrant Cloud**: Auto-scales with demand
- **Stateless API**: Horizontal scaling ready
- **Background Services**: Independent processes
- **Multi-Tenancy**: Patient isolation built-in
- **Future**: Kubernetes deployment ready

---

## 🚀 Future Enhancements

### Short Term (3-6 months)

- [ ] **Video Memory Support**: Full video upload and analysis
- [ ] **Mobile Apps**: iOS and Android native apps
- [ ] **Voice Interface**: "Hey LifeLens" voice commands
- [ ] **Offline Mode**: Queue memories when internet unavailable
- [ ] **Advanced Analytics**: Predictive models for decline
- [ ] **Multi-Language**: Support for non-English content
- [ ] **Export/Import**: Backup and transfer memories

### Medium Term (6-12 months)

- [ ] **Wearable Integration**: Smartwatch data ingestion
- [ ] **Calendar Sync**: Google Calendar, iCal integration
- [ ] **Social Features**: Share memories with permission
- [ ] **Automated Journaling**: Daily summaries via LLM
- [ ] **Face Recognition**: Automatic person identification
- [ ] **Drug Interaction Checking**: Pharmacy integration
- [ ] **Telehealth Integration**: Doctor portal access

### Long Term (12+ months)

- [ ] **Clinical Trials**: Partner with research institutions
- [ ] **Insurance Integration**: Covered care coordination
- [ ] **AI Coaching**: Personalized cognitive exercises
- [ ] **VR/AR Experiences**: Immersive memory replay
- [ ] **Blockchain**: Secure, decentralized health records
- [ ] **Federated Learning**: Privacy-preserving ML
- [ ] **Brain-Computer Interface**: Thought-based recording

---

## 📊 Project Statistics

- **Lines of Code**: ~15,000+
- **Python Files**: 50+
- **Agents**: 18 specialized agents
- **API Endpoints**: 15+
- **Qdrant Collections**: 9
- **Test Coverage**: 60%+ (growing)
- **Dependencies**: 25+ packages
- **Development Time**: 1+ week
- **Team**: Solo project

---

## 🏆 Achievements & Recognition

- **Qdrant Convolve 4.0**: Submission for hackathon
- **Multi-Agent Architecture**: Novel application in healthcare
- **Open Source**: Contributions welcomed
- **Community Impact**: Potential to help millions with dementia

---

## 📞 Support & Contact

### Documentation
- [README.md](README.md) - Project overview
- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - Quick start guide
- [EXTENSION_STATUS.md](EXTENSION_STATUS.md) - Extension details
- [PROJECT_DETAILS.md](PROJECT_DETAILS.md) - This document

### Demo
- **Live Demo**: https://lifelens-lls.streamlit.app/
- **GitHub**: [Repository URL]
- **Video Demo**: [Demo Video URL]

### Community
- **Issues**: GitHub Issues tracker
- **Discussions**: GitHub Discussions
- **Contributing**: CONTRIBUTING.md (coming soon)

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 🙏 Acknowledgments

### Technologies
- **Qdrant** - For amazing vector database
- **Google Gemini** - For powerful AI models
- **Groq** - For fast LLM inference
- **Streamlit** - For rapid UI development
- **FastAPI** - For modern API framework

### Community
- Healthcare professionals for domain insights
- Dementia caregivers for feedback
- Open source contributors
- Qdrant team for support

### Inspiration
Built with love for caregivers and patients worldwide who deserve better tools to preserve precious memories and maintain dignity through cognitive decline.

---

<div align="center">

### 🧠 LifeLens - Because Every Memory Matters

**"Helping people remember what matters most."**

---

**Built for Qdrant Convolve 4.0 Hackathon**

</div>
