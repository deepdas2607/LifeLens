<div align="center">

# 🧠 LifeLens  
### **AI-Powered Multimodal Memory Companion for Dementia Care**

_Addressing Memory Loss • Strengthening Relationships • Enhancing Care_

[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-4B0082?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203%20Inference-1A73E8?logo=groq&logoColor=white)](https://groq.com/)
[![Gemini](https://img.shields.io/badge/Gemini-1.5%20Flash-4285F4?logo=google&logoColor=white)](https://aistudio.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Live%20Demo-brightgreen)](https://lifelens-lls.streamlit.app/)

---

### **“Because memories deserve to be remembered.”**

🔗 **Live App:** https://lifelens-lls.streamlit.app/

</div>

---

## 🌟 Overview
LifeLens is an AI-powered, multimodal memory assistant designed for dementia and Alzheimer’s patients. The system supports:

- Images (captioned via Gemini)
- Audio (transcribed via Whisper)
- Text notes
- Moods & sentiments
- Locations
- People tagging
- Milestones

All stored in **Qdrant** with long-term memory retrieval using **semantic search** and **LLM reasoning**.

---

# 🧩 Why Qdrant Is the Core of LifeLens

LifeLens uses Qdrant for:

### 🔍 Multimodal Semantic Search
- Stores dense embeddings for image captions, audio transcripts, text notes  
- Enables natural language recall  
- Supports hybrid metadata filtering  

### 🧠 Long-Term Memory
- Persistent storage of all memories  
- No overwriting — everything remains retrievable  

### 🎯 Recommendations
- Related memory graph  
- Person similarity  
- Mood-based memory exploration  

### ⚙️ Real-Time Vector Search
- Low latency  
- Scalable  
- Ideal for memory-based AI agents  

### 📦 Memory Payload Structure

```json
{
  "type": "image",
  "timestamp": 1700000000,
  "caption": "A happy person standing near a beach",
  "transcript": null,
  "content": null,
  "people": ["John"],
  "mood": "happy",
  "milestone": true,
  "location": "Mumbai, India",
  "lat": 19.076,
  "lon": 72.8777,
  "raw_media_b64": "..."
}
```

---

## 🎯 Key Features

### 🔐 Security & Multi-User Roles
- Patients  
- Caretakers  
- Family (view-only)  
- SHA-256 login  
- Session-based authentication  

### 📸 Memory Ingestion
- Image captioning (Gemini 1.5 Flash)  
- Audio transcription (Groq Whisper)  
- Text notes  
- Mood detection  
- People tagging  
- Milestone support  

### 🔍 Retrieval & Reasoning
- Semantic search using Qdrant  
- Voice search  
- Related memory suggestions  
- TTS responses  

### 🛡 Caretaker Dashboard
- Memory analytics  
- Mood trends  
- People gallery  
- Memory book export  
- Manage memory requests  

### 👨‍👩‍👧 Family Portal
- Timeline  
- View-only gallery  
- Submit memory requests  

### 🗺 Location Mapping
- OSM-based map view  
- Geocoding  
- Color-coded markers  

---

# 🏛 System Architecture

Below are **fully GitHub-safe Mermaid diagrams**, validated for correct rendering.

---

## 🛰 High-Level Architecture

```mermaid
flowchart LR

UI[Streamlit Web App] --> MP[Memory Processing Layer]

MP --> IMG[Gemini Image Captioning]
MP --> AUD[Whisper Audio Transcription]
MP --> TXT[Text Preprocessing]

IMG --> EMB[FastEmbed Embeddings]
AUD --> EMB
TXT --> EMB

EMB --> QDR[Qdrant Vector Database]

SRCH[User Search Query] --> QEMB[Query Embedding via FastEmbed]
QEMB --> QDR
QDR --> RES[Retrieved Memories]

RES --> LLM[Groq LLaMA3 Reasoning]
LLM --> OUT[Final Response with Evidence and TTS]
```

---

## 🔄 Memory Retrieval Flow

```mermaid
flowchart TD
    QRY[User Query] --> EMBQ[Embed Query]
    EMBQ --> FILT[Apply Time and Metadata Filters]
    FILT --> QD[Qdrant Search]
    QD --> TOPK[Top-k Relevant Memories]
    TOPK --> LLM[LLM Grounded Reasoning]
    LLM --> RESP[Final Answer with Evidence]
```

---

## 🗄 Qdrant Collection Architecture

```mermaid
flowchart TD

COL[Lifelens Memory Collection] --> V[384-d Vector]

COL --> P[Payload Schema]

P --> T1[Memory Type]
P --> TS[Timestamp]
P --> CAP[Caption or Transcript]
P --> PPL[People Array]
P --> MD[Mood]
P --> MS[Milestone]
P --> LOC[Location Data]
P --> B64[Base64 Media]
```

---

# 🧱 Technology Stack

### **Frontend**
- Streamlit + Custom CSS

### **AI Processing**
- Google Gemini 1.5 Flash  
- Groq Whisper  
- Groq LLaMA-3  
- FastEmbed

### **Vector Storage**
- Qdrant Cloud

### **Mapping**
- OpenStreetMap  
- geopy

### **Security**
- SHA-256 password hashing  
- Session management  

---

# 🚀 Quick Start

```bash
git clone https://github.com/yourusername/lifelens.git
cd lifelens
pip install -r requirements.txt
streamlit run app.py
```

### 🔐 Add Secrets (Streamlit Cloud)

`/.streamlit/secrets.toml`:

```toml
QDRANT_URL = "..."
QDRANT_API_KEY = "..."
GROQ_API_KEY = "..."
GEMINI_API_KEY = "..."
```

---

# 🛣 Roadmap

- MFA login  
- On-device face recognition  
- Video memories  
- Mobile app  
- Multi-language support  

---

# 📄 Note
Open for Contributions and Forking

---

<div align="center">

### ❤️ _LifeLens — Bringing Memories Back to Life._

</div>
