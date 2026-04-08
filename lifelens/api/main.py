from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import sys
import jwt
import time
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from lifelens.config import QDRANT_COLLECTION_NAME, JWT_SECRET, JWT_ALGORITHM
from lifelens.auth.users import authenticate
from lifelens.qdrant.client import get_qdrant_client
from lifelens.retrieval.search_engine import search_memories
from lifelens.retrieval.reasoning import get_answer
from lifelens.ingestion.upsert_memory import upsert_memory
from qdrant_client.http import models

# Initialize App
app = FastAPI(title="LifeLens API", description="Backend for Browser Extension", version="1.0.0")

# CORS config - Allow extension to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

class SearchRequest(BaseModel):
    query: str
    patient_id: str
    top_k: int = 5

class MemoryCreate(BaseModel):
    content: str
    patient_id: str
    tags: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    location_text: Optional[str] = None

# --- Dependencies ---
def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
    
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Token")

# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "ok", "service": "LifeLens API"}

@app.post("/api/auth/login", response_model=Token)
def login(request: LoginRequest):
    user = authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "full_name": user["full_name"],
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    
    # Check if patients are assigned (for caretakers)
    if "patients" in user:
        payload["patients"] = user["patients"]
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_info": {
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "patient_id": user["patient_id"],  # Added for extension
            "patients": user.get("patients", [])
        }
    }

@app.post("/api/search")
def search(request: SearchRequest, user: dict = Depends(verify_token)):
    try:
        client = get_qdrant_client()
        
        # Verify access
        if user["role"] == "caretaker" and request.patient_id not in user.get("patients", []):
            raise HTTPException(status_code=403, detail="Access to patient denied")
        
        # Don't allow empty queries for search
        if not request.query or request.query.strip() == "":
            raise HTTPException(status_code=400, detail="Query cannot be empty")
            
        memories = search_memories(
            client=client, 
            query=request.query, 
            patient_id=request.patient_id, 
            top_k=request.top_k
        )
        
        # Filter by score (threshold 0.45 to remove noise)
        memories = [m for m in memories if m.get("score", 0) > 0.45]
        
        answer = get_answer(request.query, memories)
        
        return {
            "answer": answer,
            "memories": memories
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memories/{patient_id}")
def get_recent_memories(patient_id: str, limit: int = 20, user: dict = Depends(verify_token)):
    """Get recent memories for Memory Lane view without requiring a search query"""
    try:
        client = get_qdrant_client()
        
        # Verify access
        if user["role"] == "caretaker" and patient_id not in user.get("patients", []):
            raise HTTPException(status_code=403, detail="Access to patient denied")
        
        # Use scroll to get recent memories
        results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="patient_id", match=models.MatchValue(value=patient_id))]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )[0]
        
        # Format results
        memories = []
        for point in results:
            payload = point.payload
            memories.append({
                "type": payload.get("type"),
                "content": payload.get("content"),
                "caption": payload.get("caption"),
                "transcript": payload.get("transcript"),
                "analysis": payload.get("analysis"),
                "timestamp": payload.get("timestamp"),
                "person_tags": payload.get("person_tags"),
                "location": payload.get("location"),
                "sentiment": payload.get("sentiment")
            })
        
        # Sort by timestamp descending
        memories.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return {"memories": memories}
        
    except Exception as e:
        logger.error(f"Get memories failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/create")
def create_memory(request: MemoryCreate, user: dict = Depends(verify_token)):
    try:
        client = get_qdrant_client()
        
        if user["role"] == "caretaker" and request.patient_id not in user.get("patients", []):
            raise HTTPException(status_code=403, detail="Access to patient denied")

        data = {
            "patient_id": request.patient_id,
            "content": request.content,
            "timestamp": int(time.time()),
            "source": "extension"
        }
        
        if request.tags:
            data["person_tags"] = request.tags
            
        if request.url:
            data["url"] = request.url
            data["title"] = request.title
        
        if request.location_text:
            data["location"] = {"name": request.location_text}
            
        upsert_memory(client, "text", data)
        return {"status": "success", "message": "Memory created"}
        
    except Exception as e:
        logger.error(f"Create memory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/image")
async def upload_image(
    file: UploadFile = File(...), 
    patient_id: str = Form(...),
    caption: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    user: dict = Depends(verify_token)
):
    try:
        client = get_qdrant_client()
        
        from lifelens.ingestion.image_processor import process_image
        
        # Save temp file
        temp_filename = f"temp_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        try:
            # Re-open for processing (API expects file-like object or path)
            with open(temp_filename, "rb") as f:
                result = process_image(f)
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        data = {
            "patient_id": patient_id,
            "image_base64": result["image_base64"],
            "caption": result["caption"],
            "sentiment": result.get("sentiment"),
            "source": "extension"
        }
        
        if tags:
            data["person_tags"] = tags
        
        # Override caption if provided manually
        if caption:
            data["caption"] = f"{caption} ({result['caption']})"

        upsert_memory(client, "image", data)
        return {"status": "success", "message": "Image memory created"}

    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/audio")
async def upload_audio(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    user: dict = Depends(verify_token)
):
    try:
        from lifelens.ingestion.audio_processor import process_audio
        
        # Save temp file
        temp_filename = f"temp_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        try:
            # Re-open for processing
            result = process_audio(temp_filename) # process_audio handles path string or file-like? checking code...
             # Actually audio_processor.process_audio expects a file path usually to pass to whisper/gemini
             # Let's check audio_processor in a separate step if unsure, but usually path string is safer for ffmpeg tools
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        client = get_qdrant_client()
        data = {
            "patient_id": patient_id,
            "audio_base64": result["audio_base64"],
            "transcript": result["transcript"],
            "source": "extension"
        }
        
        upsert_memory(client, "audio", data)
        return {"status": "success", "message": "Audio memory created"}

    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
