"""
LifeLens Trigger Agent - Agent-Generated Reminders & Notifications

This module analyzes Qdrant memory patterns and generates intelligent triggers
to help caregivers capture important moments and stay engaged with LifeLens.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import (
    QDRANT_COLLECTION_NAME, 
    MEMORY_GAP_THRESHOLD_MINUTES, 
    PHOTO_GAP_THRESHOLD_MINUTES
)
import time

logger = logging.getLogger(__name__)


def get_patient_stats(client: QdrantClient, patient_id: str) -> Dict:
    """
    Analyzes patient memory patterns from Qdrant.
    
    Args:
        client: QdrantClient instance
        query: Patient ID to analyze
        
    Returns:
        Dictionary containing patient statistics
    """
    try:
        # Get all memories for this patient
        scroll_result = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        memories = scroll_result[0]
        
        if not memories:
            return {
                "total_memories": 0,
                "minutes_since_last_memory": float('inf'),
                "minutes_since_last_photo": float('inf'),
                "negative_mood_count": 0,
                "total_mood_count": 0,
                "untagged_people_count": 0,
                "milestone_count": 0,
                "repeated_questions": []
            }
        
        # Calculate statistics
        now = time.time()
        timestamps = []
        photo_timestamps = []
        negative_moods = 0
        total_moods = 0
        untagged_people = 0
        milestones = 0
        
        for memory in memories:
            payload = memory.payload
            
            # Collect timestamps
            if "timestamp" in payload:
                timestamps.append(payload["timestamp"])
                
                # Type-specific timestamps
                if payload.get("type") == "image":
                    photo_timestamps.append(payload["timestamp"])
            
            # Mood analysis
            sentiment = payload.get("sentiment", "").lower()
            if sentiment:
                total_moods += 1
                if sentiment in ["sad", "angry", "fearful", "negative"]:
                    negative_moods += 1
            
            # Check for untagged people
            person_tags = payload.get("person_tags", [])
            if not person_tags or (isinstance(person_tags, list) and len(person_tags) == 0):
                if payload.get("type") in ["image", "video"]:
                    untagged_people += 1
            
            # Count milestones
            if payload.get("milestone", False):
                milestones += 1
        
        # Calculate minutes since last memory
        minutes_since_last = float('inf')
        if timestamps:
            latest_timestamp = max(timestamps)
            minutes_since_last = (now - latest_timestamp) / 60
        
        # Calculate minutes since last photo
        minutes_since_photo = float('inf')
        if photo_timestamps:
            latest_photo = max(photo_timestamps)
            minutes_since_photo = (now - latest_photo) / 60
        
        return {
            "total_memories": len(memories),
            "minutes_since_last_memory": minutes_since_last,
            "minutes_since_last_photo": minutes_since_photo,
            "negative_mood_count": negative_moods,
            "total_mood_count": total_moods,
            "negative_mood_ratio": negative_moods / total_moods if total_moods > 0 else 0,
            "untagged_people_count": untagged_people,
            "milestone_count": milestones,
            "repeated_questions": []
        }
        
    except Exception as e:
        logger.error(f"Error getting patient stats: {e}")
        return {
            "total_memories": 0,
            "minutes_since_last_memory": 0,
            "error": str(e)
        }


def detect_memory_gaps(stats: Dict) -> Optional[Dict]:
    """
    Detects when no memories have been logged recently (using config threshold).
    """
    minutes = stats.get("minutes_since_last_memory", 0)
    if minutes >= MEMORY_GAP_THRESHOLD_MINUTES:
        time_str = "a long time" if minutes == float('inf') else f"{int(minutes)} minutes"
        return {
            "type": "memory_gap",
            "title": "Quick Recap Reminder",
            "message": f"No memories logged in {time_str}. (Demo Mode)",
            "priority": "high",
            "action": "capture_memory",
            "timestamp": datetime.now().isoformat()
        }
    return None


def detect_mood_trends(stats: Dict) -> Optional[Dict]:
    """
    Analyzes negative mood trends.
    """
    if stats.get("total_mood_count", 0) >= 3: # Reduced threshold for demo
        if stats.get("negative_mood_ratio", 0) > 0.5:
            return {
                "type": "mood_trend",
                "title": "Wellness Check (Demo)",
                "message": f"Recent mood trend detected. Please check in. (Demo Mode)",
                "priority": "urgent",
                "action": "notify_caretaker",
                "timestamp": datetime.now().isoformat()
            }
    return None


def detect_media_gaps(stats: Dict) -> Optional[Dict]:
    """
    Checks for lack of photos recently (using config threshold).
    """
    minutes = stats.get("minutes_since_last_photo", 0)
    if minutes >= PHOTO_GAP_THRESHOLD_MINUTES:
        time_str = "a long time" if minutes == float('inf') else f"{int(minutes)} minutes"
        return {
            "type": "media_gap",
            "title": "Photo Suggestion (Demo)",
            "message": f"No photos captured in {time_str}. (Demo Mode)",
            "priority": "medium",
            "action": "capture_photo",
            "timestamp": datetime.now().isoformat()
        }
    return None



def detect_untagged_people(stats: Dict) -> Optional[Dict]:
    """
    Detects photos/videos with untagged people.
    
    Args:
        stats: Patient statistics dictionary
        
    Returns:
        Trigger dictionary or None
    """
    if stats.get("untagged_people_count", 0) >= 3:
        return {
            "type": "untagged_people",
            "title": "Tag People in Photos",
            "message": f"{stats['untagged_people_count']} photos/videos have no people tagged. Adding names helps with memory recall.",
            "priority": "low",
            "action": "tag_people",
            "timestamp": datetime.now().isoformat()
        }
    return None


def detect_milestone_anniversaries(client: QdrantClient, patient_id: str) -> Optional[Dict]:
    """
    Finds upcoming milestone anniversaries.
    
    Args:
        client: QdrantClient instance
        patient_id: Patient ID to check
        
    Returns:
        Trigger dictionary or None
    """
    try:
        # Get milestone memories
        scroll_result = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="category",
                        match=models.MatchValue(value="Achievement")
                    )
                ]
            ),
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        milestones = scroll_result[0]
        now = datetime.now()
        
        for milestone in milestones:
            payload = milestone.payload
            timestamp = payload.get("timestamp")
            
            if timestamp:
                milestone_date = datetime.fromtimestamp(timestamp)
                
                # Check if anniversary is within next 7 days
                days_until = (milestone_date.replace(year=now.year) - now).days
                
                if 0 <= days_until <= 7:
                    return {
                        "type": "milestone_anniversary",
                        "title": "Milestone Anniversary Coming Up",
                        "message": f"A milestone memory anniversary is in {days_until} days. Consider adding new memories to celebrate!",
                        "priority": "medium",
                        "action": "capture_memory",
                        "timestamp": datetime.now().isoformat()
                    }
        
    except Exception as e:
        logger.error(f"Error detecting milestone anniversaries: {e}")
    
    return None


def get_trigger_priority(trigger_type: str) -> str:
    """
    Assigns priority levels to triggers.
    
    Args:
        trigger_type: Type of trigger
        
    Returns:
        Priority level (urgent, high, medium, low)
    """
    priority_map = {
        "mood_trend": "urgent",
        "memory_gap": "high",
        "media_gap": "medium",
        "milestone_anniversary": "medium",
        "untagged_people": "low"
    }
    return priority_map.get(trigger_type, "medium")


def generate_triggers(client: QdrantClient, patient_id: str) -> List[Dict]:
    """
    Main function that generates all triggers for a patient.
    
    Args:
        client: QdrantClient instance
        patient_id: Patient ID to generate triggers for
        
    Returns:
        List of trigger dictionaries
    """
    triggers = []
    
    try:
        # Get patient statistics
        stats = get_patient_stats(client, patient_id)
        
        # Run all detection functions
        detectors = [
            detect_memory_gaps,
            detect_mood_trends,
            detect_media_gaps,
            detect_untagged_people
        ]
        
        for detector in detectors:
            trigger = detector(stats)
            if trigger:
                triggers.append(trigger)
        
        # Check milestone anniversaries (requires client)
        milestone_trigger = detect_milestone_anniversaries(client, patient_id)
        if milestone_trigger:
            triggers.append(milestone_trigger)
        
        # Sort by priority
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        triggers.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
        
        logger.info(f"Generated {len(triggers)} triggers for patient {patient_id}")
        
    except Exception as e:
        logger.error(f"Error generating triggers: {e}")
    
    return triggers
