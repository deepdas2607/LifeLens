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
            model="models/text-embedding-004",
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
        payload["source_audio_base64"] = data["base64"]
        payload["sentiment"] = data.get("sentiment", "Neutral")
        if "location" in data:
            payload["location"] = data["location"]
        text_to_embed = data["transcript"]
        
    elif memory_type == "text":
        payload["content"] = data["content"]
        if "location" in data:
            payload["location"] = data["location"]
        text_to_embed = data["content"]
    
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
        return point_id
    except Exception as e:
        logging.error(f"Failed to upsert memory: {e}")
        raise e
