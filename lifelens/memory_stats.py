"""
Memory Statistics Module

Analytics for agent decision-making.
Provides patient statistics and pattern detection.
"""

import logging
from typing import Dict
from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import QDRANT_COLLECTION_NAME
import time

logger = logging.getLogger(__name__)


def get_patient_stats(patient_id: str, qdrant_client: QdrantClient) -> Dict:
    """
    Aggregates comprehensive memory statistics for a patient.
    
    Args:
        patient_id: Patient identifier
        qdrant_client: Qdrant client instance
        
    Returns:
        Dictionary with patient statistics
    """
    
    try:
        # Fetch all memories for patient (excluding agent decisions)
        results = qdrant_client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ],
                must_not=[
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="agent_decision")
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )[0]
        
        memories = [p.payload for p in results]
        
        # Calculate statistics
        total_count = len(memories)
        
        # Count by type
        types_count = {}
        for mem in memories:
            mem_type = mem.get("type", "unknown")
            types_count[mem_type] = types_count.get(mem_type, 0) + 1
        
        # Recent memories (last 7 days)
        week_ago = int(time.time()) - (7 * 24 * 60 * 60)
        recent_memories = [m for m in memories if m.get("timestamp", 0) > week_ago]
        recent_count = len(recent_memories)
        
        # Last upload time
        timestamps = [m.get("timestamp", 0) for m in memories]
        last_upload = max(timestamps) if timestamps else None
        
        # Time since last upload (minutes)
        time_since_last = None
        if last_upload:
            time_since_last = (int(time.time()) - last_upload) / 60
        
        # Sentiment distribution
        sentiments = {}
        for mem in memories:
            sentiment = mem.get("sentiment", "Neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        
        # Photos with people
        photos_with_people = sum(1 for m in memories 
                                if m.get("type") == "image" and m.get("person_tags"))
        
        # Photos without people tags
        photos_without_tags = sum(1 for m in memories 
                                 if m.get("type") == "image" and not m.get("person_tags"))
        
        stats = {
            "total_memories": total_count,
            "types_count": types_count,
            "recent_count": recent_count,
            "last_upload_timestamp": last_upload,
            "time_since_last_upload_minutes": time_since_last,
            "sentiments": sentiments,
            "photos_with_people": photos_with_people,
            "photos_without_tags": photos_without_tags,
            "recent_memories": recent_memories
        }
        
        logger.info(f"Patient {patient_id} stats: {total_count} total, {recent_count} recent")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get patient stats: {e}")
        return {
            "total_memories": 0,
            "types_count": {},
            "recent_count": 0,
            "last_upload_timestamp": None,
            "time_since_last_upload_minutes": None,
            "sentiments": {},
            "photos_with_people": 0,
            "photos_without_tags": 0,
            "recent_memories": []
        }


def detect_patterns(patient_id: str, qdrant_client: QdrantClient) -> Dict:
    """
    Identifies trends and patterns in patient memories.
    
    Args:
        patient_id: Patient identifier
        qdrant_client: Qdrant client instance
        
    Returns:
        Dictionary with detected patterns
    """
    
    stats = get_patient_stats(patient_id, qdrant_client)
    
    patterns = {
        "has_memory_gap": False,
        "has_photo_gap": False,
        "has_negative_trend": False,
        "has_untagged_photos": False,
        "is_active": False
    }
    
    # Memory gap (no uploads in last 5 minutes for demo)
    if stats["time_since_last_upload_minutes"] and stats["time_since_last_upload_minutes"] > 5:
        patterns["has_memory_gap"] = True
    
    # Photo gap (no photos in last 10 minutes for demo)
    recent_photos = [m for m in stats["recent_memories"] if m.get("type") == "image"]
    if len(recent_photos) == 0 and stats["time_since_last_upload_minutes"] and stats["time_since_last_upload_minutes"] > 10:
        patterns["has_photo_gap"] = True
    
    # Negative mood trend
    sentiments = stats["sentiments"]
    negative_count = sentiments.get("Sad", 0) + sentiments.get("Angry", 0)
    total_with_sentiment = sum(sentiments.values())
    if total_with_sentiment > 0 and (negative_count / total_with_sentiment) > 0.5:
        patterns["has_negative_trend"] = True
    
    # Untagged photos
    if stats["photos_without_tags"] > 0:
        patterns["has_untagged_photos"] = True
    
    # Active user (uploaded in last 24 hours)
    if stats["time_since_last_upload_minutes"] and stats["time_since_last_upload_minutes"] < (24 * 60):
        patterns["is_active"] = True
    
    return patterns
