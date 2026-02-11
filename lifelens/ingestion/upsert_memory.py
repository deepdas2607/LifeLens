import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')

import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import QDRANT_COLLECTION_NAME, GEMINI_API_KEY
import uuid
import time
import logging

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_embedding(text: str):
    """
    Generates embedding using Gemini API.
    """
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document",
            title="Embedding of single text"
        )
        return result['embedding']
    except Exception as e:
        logging.error(f"Failed to generate embedding: {e}")
        raise e

def upsert_memory(client: QdrantClient, memory_type: str, data: dict):
    """
    Upserts a memory item into Qdrant.
    
    Args:
        client: QdrantClient instance
        memory_type: 'image', 'audio', or 'text'
        data: Dictionary containing content/caption/transcript and other metadata
    """
    
    # Prepare payload and text to embed
    payload = {
        "type": memory_type,
        "timestamp": int(time.time()),
        "patient_id": data.get("patient_id", "unknown")
    }
    
    # Add optional category/milestone flag
    if "category" in data:
        payload["category"] = data["category"]
    elif "is_milestone" in data:
        payload["is_milestone"] = data["is_milestone"]
    
    text_to_embed = ""
    
    if memory_type == "image":
        payload["caption"] = data["caption"]
        payload["source_image_base64"] = data["base64"]
        if "person_tags" in data:
            payload["person_tags"] = data["person_tags"]
        if "location" in data:
            payload["location"] = data["location"]
        text_to_embed = data["caption"]
        
    elif memory_type == "audio":
        payload["transcript"] = data["transcript"]
        payload["source_audio_base64"] = data.get("base64") or data.get("audio_base64")
        payload["sentiment"] = data.get("sentiment", "Neutral")
        if "location" in data:
            payload["location"] = data["location"]
        text_to_embed = data["transcript"]
        
    elif memory_type == "text":
        payload["content"] = data["content"]
        if "location" in data:
            payload["location"] = data["location"]
        text_to_embed = data["content"]
        
    elif memory_type == "video":
        # Video analysis comes as a text block (summary)
        payload["analysis"] = data.get("analysis", "")
        # Try to parse mood if present in text, or simple regex? 
        # For now, just store the full analysis.
        if "location" in data:
            payload["location"] = data["location"]
        if "person_tags" in data:
            payload["person_tags"] = data["person_tags"]
        if "video_path" in data:
            payload["video_path"] = data["video_path"]
        text_to_embed = data.get("analysis", "")
    
    if not text_to_embed:
        raise ValueError("No text content available to embed.")

    # Generate Embedding using Gemini
    vector = get_embedding(text_to_embed)
    
    # Create Point
    point_id = str(uuid.uuid4())
    
    point = models.PointStruct(
        id=point_id,
        vector=vector,
        payload=payload
    )
    
    # Upsert
    try:
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[point]
        )
        logging.info(f"Successfully upserted {memory_type} memory with ID {point_id}")
        
        # Also upsert to mood_events collection if mood data is present
        if "sentiment" in payload or "mood" in data:
            _upsert_mood_event(client, payload, vector, data)
        
        return point_id
    except Exception as e:
        logging.error(f"Failed to upsert memory: {e}")
        raise e


def _upsert_mood_event(client: QdrantClient, memory_payload: dict, vector: list, data: dict):
    """
    Stores mood event in dedicated mood_events collection.
    
    This enables the Mood Intelligence Agent to analyze time-series mood data.
    """
    try:
        from datetime import datetime
        
        # Extract mood information
        mood = data.get("mood") or memory_payload.get("sentiment", "Neutral")
        
        # Convert sentiment to mood if needed
        sentiment_to_mood = {
            "Happy": "happy",
            "Sad": "sad",
            "Angry": "angry",
            "Confused": "confused",
            "Neutral": "neutral",
            "Anxious": "anxious",
            "Excited": "excited"
        }
        mood = sentiment_to_mood.get(mood, mood.lower())
        
        # Calculate mood score
        from lifelens.agents.mood_agent import _convert_mood_to_score
        mood_score = _convert_mood_to_score(mood)
        
        # Extract metadata
        timestamp = data.get("timestamp")
        if not timestamp:
            timestamp = datetime.utcnow().isoformat() + "Z"
        elif not timestamp.endswith("Z"):
            # Ensure timestamp has Z suffix for UTC
            timestamp = timestamp.rstrip() + "Z" if "+" not in timestamp else timestamp
        patient_id = memory_payload.get("patient_id", "unknown")
        
        # Build mood event payload
        mood_payload = {
            "patient_id": patient_id,
            "timestamp": timestamp,
            "mood": mood,
            "mood_score": mood_score,
            "source": memory_payload.get("type", "unknown"),
            "people": data.get("person_tags", []) or memory_payload.get("person_tags", []),
            "milestone": memory_payload.get("is_milestone", False),
            "location": memory_payload.get("location", "")
        }
        
        # Store in mood_events collection
        mood_point_id = str(uuid.uuid4())
        mood_point = models.PointStruct(
            id=mood_point_id,
            vector=vector,  # Same embedding as memory
            payload=mood_payload
        )
        
        client.upsert(
            collection_name="mood_events",
            points=[mood_point]
        )
        
        logging.info(f"Mood event stored: {mood} (score: {mood_score:.2f}) for patient {patient_id}")
        
    except Exception as e:
        # Don't fail the main upsert if mood storage fails
        logging.warning(f"Failed to store mood event: {e}")
