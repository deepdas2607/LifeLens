"""
Medication Management Utilities

Helper functions for medication tracking and event logging.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)


def record_medication_event(client: QdrantClient, event_data: Dict) -> bool:
    """
    Records a medication event (taken, skipped, missed) to Qdrant.
    
    Args:
        client: Qdrant client instance
        event_data: Dictionary containing:
            - patient_id: Patient identifier
            - medication_id: Medication identifier
            - status: "taken", "skipped", or "missed"
            - reported_by: "patient" or "caretaker"
            - note: Optional free-text note
            - dose_time: Scheduled time (HH:MM)
            - dose_date: Date of dose (YYYY-MM-DD)
            
    Returns:
        True if successful, False otherwise
    """
    try:
        required_fields = ["patient_id", "medication_id", "status", "reported_by"]
        for field in required_fields:
            if field not in event_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Generate embedding for note (if provided)
        note = event_data.get("note", "")
        if note:
            try:
                embedding_result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=note,
                    task_type="retrieval_document"
                )
                vector = embedding_result["embedding"]
            except:
                vector = [0.0] * 3072
        else:
            # Use zero vector if no note
            vector = [0.0] * 3072
        
        # Get current timestamp
        now = datetime.now()
        
        # Prepare payload with both ISO string and Unix timestamp
        payload = {
            "patient_id": event_data["patient_id"],
            "medication_id": event_data["medication_id"],
            "timestamp": now.timestamp(),  # Store as Unix timestamp for range queries
            "timestamp_iso": now.isoformat(),  # Keep ISO for display
            "status": event_data["status"],
            "reported_by": event_data["reported_by"],
            "note": note,
            "dose_time": event_data.get("dose_time", ""),
            "dose_date": event_data.get("dose_date", now.date().isoformat())
        }
        
        # Store in medication_events collection
        client.upsert(
            collection_name="medication_events",
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload
                )
            ]
        )
        
        logger.info(f"✅ Recorded medication event: {event_data['status']} for {event_data['medication_id']} at {event_data.get('dose_time')}")
        return True
        
    except Exception as e:
        logger.error(f"Error recording medication event: {e}", exc_info=True)
        return False


def get_medication_history(client: QdrantClient, patient_id: str, 
                          medication_id: Optional[str] = None,
                          days: int = 30) -> List[Dict]:
    """
    Retrieves medication history for a patient.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        medication_id: Optional medication filter
        days: Number of days to retrieve (default: 30)
        
    Returns:
        List of medication events
    """
    try:
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=days)
        
        # Convert to Unix timestamp for Range query
        start_timestamp = start_date.timestamp()
        
        filter_conditions = [
            models.FieldCondition(
                key="patient_id",
                match=models.MatchValue(value=patient_id)
            ),
            models.FieldCondition(
                key="timestamp",
                range=models.Range(gte=start_timestamp)
            )
        ]
        
        if medication_id:
            filter_conditions.append(
                models.FieldCondition(
                    key="medication_id",
                    match=models.MatchValue(value=medication_id)
                )
            )
        
        results = client.scroll(
            collection_name="medication_events",
            scroll_filter=models.Filter(must=filter_conditions),
            limit=500
        )[0]
        
        events = [point.payload for point in results]
        # Sort by timestamp descending
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return events
        
    except Exception as e:
        logger.error(f"Error retrieving medication history: {e}")
        return []


def get_adherence_calendar(client: QdrantClient, patient_id: str, 
                          days: int = 30) -> Dict:
    """
    Creates a calendar view of medication adherence.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        days: Number of days to include
        
    Returns:
        Dictionary with date-based adherence data
    """
    events = get_medication_history(client, patient_id, days=days)
    
    calendar_data = {}
    
    for event in events:
        date = event.get("dose_date", "")
        if not date:
            # Extract from timestamp
            timestamp = event.get("timestamp", "")
            if timestamp:
                date = datetime.fromisoformat(timestamp).date().isoformat()
        
        if date not in calendar_data:
            calendar_data[date] = {
                "taken": 0,
                "missed": 0,
                "skipped": 0,
                "total": 0
            }
        
        status = event.get("status", "")
        calendar_data[date]["total"] += 1
        calendar_data[date][status] = calendar_data[date].get(status, 0) + 1
    
    return calendar_data


def get_medication_details(client: QdrantClient, medication_id: str, 
                          patient_id: str) -> Optional[Dict]:
    """
    Retrieves details for a specific medication.
    
    Args:
        client: Qdrant client instance
        medication_id: Medication identifier
        patient_id: Patient identifier
        
    Returns:
        Medication details dictionary or None if not found
    """
    try:
        results = client.scroll(
            collection_name="medications",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="medication_id",
                        match=models.MatchValue(value=medication_id)
                    )
                ]
            ),
            limit=1
        )[0]
        
        if results:
            return results[0].payload
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving medication details: {e}")
        return None


def get_all_patient_medications(client: QdrantClient, patient_id: str, 
                                active_only: bool = True) -> List[Dict]:
    """
    Retrieves all medications for a patient.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        active_only: If True, only return active medications
        
    Returns:
        List of medication records
    """
    try:
        filter_conditions = [
            models.FieldCondition(
                key="patient_id",
                match=models.MatchValue(value=patient_id)
            )
        ]
        
        if active_only:
            filter_conditions.append(
                models.FieldCondition(
                    key="active",
                    match=models.MatchValue(value=True)
                )
            )
        
        results = client.scroll(
            collection_name="medications",
            scroll_filter=models.Filter(must=filter_conditions),
            limit=100
        )[0]
        
        medications = [point.payload for point in results]
        # Sort by name
        medications.sort(key=lambda x: x.get("name", ""))
        
        return medications
        
    except Exception as e:
        logger.error(f"Error retrieving patient medications: {e}")
        return []


def calculate_adherence_rate(client: QdrantClient, patient_id: str, 
                            medication_id: Optional[str] = None,
                            days: int = 7) -> float:
    """
    Calculates adherence rate for a patient or specific medication.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        medication_id: Optional medication filter
        days: Number of days to calculate over
        
    Returns:
        Adherence rate as a decimal (0.0 to 1.0)
    """
    events = get_medication_history(client, patient_id, medication_id, days)
    
    if not events:
        return 0.0
    
    taken = len([e for e in events if e.get("status") == "taken"])
    total = len(events)
    
    return taken / total if total > 0 else 0.0


def get_medication_insights_for_patient(client: QdrantClient, 
                                       patient_id: str) -> Optional[Dict]:
    """
    Retrieves the most recent adherence insights for a patient.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        
    Returns:
        Latest insights dictionary or None
    """
    try:
        results = client.scroll(
            collection_name="medication_insights",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ]
            ),
            limit=1,
            order_by=models.OrderBy(
                key="timestamp",
                direction=models.Direction.DESC
            )
        )[0]
        
        if results:
            return results[0].payload
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving medication insights: {e}")
        return None


def format_time_for_display(time_str: str) -> str:
    """
    Formats time string for display (24h to 12h format).
    
    Args:
        time_str: Time in HH:MM format
        
    Returns:
        Formatted time string
    """
    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        return time_obj.strftime("%I:%M %p")
    except:
        return time_str


def is_medication_overdue(scheduled_time: str, current_time: datetime = None) -> bool:
    """
    Checks if a medication dose is overdue.
    
    Args:
        scheduled_time: Scheduled time in HH:MM format
        current_time: Current datetime (defaults to now)
        
    Returns:
        True if overdue, False otherwise
    """
    if current_time is None:
        current_time = datetime.now()
    
    try:
        scheduled = datetime.strptime(scheduled_time, "%H:%M").time()
        scheduled_datetime = datetime.combine(current_time.date(), scheduled)
        return scheduled_datetime < current_time
    except:
        return False
