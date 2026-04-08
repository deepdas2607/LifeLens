"""
Medication Planner Agent

Validates medication schedules, avoids duplicates, confirms active dates.
Generates reminder plans and logs decisions to Qdrant.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)


def validate_medication(medication_data: Dict) -> tuple[bool, str]:
    """
    Validates medication data before storage.
    
    Args:
        medication_data: Dictionary containing medication details
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["patient_id", "name", "dosage", "schedule", "start_date"]
    
    for field in required_fields:
        if field not in medication_data or not medication_data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate schedule format
    schedule = medication_data.get("schedule", [])
    if not isinstance(schedule, list) or len(schedule) == 0:
        return False, "Schedule must be a non-empty list of times"
    
    # Validate time format (HH:MM)
    for time_str in schedule:
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return False, f"Invalid time format: {time_str}. Use HH:MM format."
    
    # Validate dates
    try:
        start_date = datetime.fromisoformat(medication_data["start_date"])
        if "end_date" in medication_data and medication_data["end_date"]:
            end_date = datetime.fromisoformat(medication_data["end_date"])
            if end_date < start_date:
                return False, "End date must be after start date"
    except ValueError:
        return False, "Invalid date format. Use ISO format (YYYY-MM-DD)"
    
    return True, ""


def check_duplicate_medications(client: QdrantClient, patient_id: str, 
                                medication_name: str) -> List[Dict]:
    """
    Check for existing active medications with the same name.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        medication_name: Name of medication to check
        
    Returns:
        List of duplicate medication records
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
                        key="active",
                        match=models.MatchValue(value=True)
                    )
                ]
            ),
            limit=100
        )[0]
        
        duplicates = []
        for point in results:
            if point.payload.get("name", "").lower() == medication_name.lower():
                duplicates.append(point.payload)
        
        return duplicates
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return []


def plan_medication_schedule(medication_data: Dict, client: QdrantClient) -> Dict:
    """
    Creates a comprehensive plan for medication management.
    
    Args:
        medication_data: Medication details
        client: Qdrant client instance
        
    Returns:
        Dictionary containing plan details and validation results
    """
    patient_id = medication_data.get("patient_id")
    medication_name = medication_data.get("name")
    
    # Validate medication data
    is_valid, error_msg = validate_medication(medication_data)
    if not is_valid:
        return {
            "success": False,
            "error": error_msg,
            "medication_id": None
        }
    
    # Check for duplicates
    duplicates = check_duplicate_medications(client, patient_id, medication_name)
    if duplicates:
        logger.warning(f"Found {len(duplicates)} duplicate active medications")
        return {
            "success": False,
            "error": f"Medication '{medication_name}' already exists for this patient",
            "duplicates": duplicates,
            "medication_id": None
        }
    
    # Generate medication ID
    medication_id = f"med_{uuid.uuid4().hex[:8]}"
    
    # Calculate total daily doses
    schedule = medication_data.get("schedule", [])
    total_daily_doses = len(schedule)
    
    # Generate embedding for medication name + notes
    try:
        text_to_embed = f"{medication_name} {medication_data.get('dosage', '')} {medication_data.get('notes', '')}"
        embedding_model = genai.GenerativeModel("models/gemini-1.5-flash")
        embedding_result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text_to_embed,
            task_type="retrieval_document"
        )
        vector = embedding_result["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Use zero vector as fallback
        vector = [0.0] * 3072
    
    # Store in Qdrant
    now = datetime.now()
    payload = {
        "patient_id": patient_id,
        "medication_id": medication_id,
        "name": medication_name,
        "dosage": medication_data.get("dosage", ""),
        "schedule": schedule,
        "start_date": medication_data.get("start_date"),
        "end_date": medication_data.get("end_date", None),
        "notes": medication_data.get("notes", ""),
        "prescribed_by": medication_data.get("prescribed_by", "caretaker"),
        "active": True,
        "created_at": now.timestamp(),
        "created_at_iso": now.isoformat(),
        "total_daily_doses": total_daily_doses
    }
    
    try:
        client.upsert(
            collection_name="medications",
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload
                )
            ]
        )
        logger.info(f"Medication {medication_id} stored successfully")
        
        # Log decision to agent_decisions or main collection
        _log_planner_decision(client, patient_id, medication_id, payload)
        
        return {
            "success": True,
            "medication_id": medication_id,
            "plan": {
                "total_daily_doses": total_daily_doses,
                "schedule": schedule,
                "reminder_plan": f"Reminders will fire at: {', '.join(schedule)}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error storing medication: {e}")
        return {
            "success": False,
            "error": str(e),
            "medication_id": None
        }


def _log_planner_decision(client: QdrantClient, patient_id: str, 
                          medication_id: str, payload: Dict):
    """
    Logs medication planning decision to Qdrant for audit trail.
    """
    try:
        now = datetime.now()
        log_payload = {
            "patient_id": patient_id,
            "agent": "medication_planner",
            "action": "schedule_medication",
            "medication_id": medication_id,
            "medication_name": payload.get("name"),
            "schedule": payload.get("schedule"),
            "timestamp": now.timestamp(),
            "timestamp_iso": now.isoformat(),
            "type": "agent_decision"
        }
        
        # Generate embedding for log
        log_text = f"Scheduled medication {payload.get('name')} for patient {patient_id}"
        embedding_result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=log_text,
            task_type="retrieval_document"
        )
        
        client.upsert(
            collection_name="lifelens_memory",
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding_result["embedding"],
                    payload=log_payload
                )
            ]
        )
        logger.info(f"Logged planner decision for {medication_id}")
        
    except Exception as e:
        logger.warning(f"Failed to log planner decision: {e}")


def update_medication(client: QdrantClient, medication_id: str, 
                     patient_id: str, updates: Dict) -> bool:
    """
    Updates an existing medication record.
    
    Args:
        client: Qdrant client instance
        medication_id: Medication identifier
        patient_id: Patient identifier
        updates: Dictionary of fields to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Find the medication point
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
        
        if not results:
            logger.error(f"Medication {medication_id} not found")
            return False
        
        point = results[0]
        updated_payload = point.payload.copy()
        updated_payload.update(updates)
        now = datetime.now()
        updated_payload["updated_at"] = now.timestamp()
        updated_payload["updated_at_iso"] = now.isoformat()
        
        # Update in Qdrant
        client.set_payload(
            collection_name="medications",
            payload=updated_payload,
            points=[point.id]
        )
        
        logger.info(f"Medication {medication_id} updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating medication: {e}")
        return False


def deactivate_medication(client: QdrantClient, medication_id: str, 
                         patient_id: str) -> bool:
    """
    Marks a medication as inactive (soft delete).
    
    Args:
        client: Qdrant client instance
        medication_id: Medication identifier
        patient_id: Patient identifier
        
    Returns:
        True if successful, False otherwise
    """
    now = datetime.now()
    return update_medication(
        client, medication_id, patient_id, 
        {"active": False, "deactivated_at": now.timestamp(), "deactivated_at_iso": now.isoformat()}
    )
