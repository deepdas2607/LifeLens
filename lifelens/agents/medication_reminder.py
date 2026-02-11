"""
Medication Reminder Agent

Sends medication reminders via in-app notifications and ntfy push.
Logs reminder delivery to Qdrant.
"""

import logging
from typing import Dict, List
from datetime import datetime
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY
from lifelens.utils.ntfy_notifications import send_ntfy

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)


def send_medication_reminder(client: QdrantClient, dose_info: Dict) -> bool:
    """
    Sends a medication reminder via ntfy and logs it to Qdrant.
    
    Args:
        client: Qdrant client instance
        dose_info: Dictionary containing dose details
        
    Returns:
        True if successful, False otherwise
    """
    patient_id = dose_info.get("patient_id")
    medication_name = dose_info.get("medication_name")
    dosage = dose_info.get("dosage")
    scheduled_time = dose_info.get("scheduled_time")
    notes = dose_info.get("notes", "")
    
    # Create reminder message
    title = "Medication Reminder"
    message = f"Time to take {medication_name} {dosage}."
    
    if scheduled_time:
        message += f"\nScheduled time: {scheduled_time}"
    
    if notes:
        message += f"\n\nNote: {notes}"
    
    message += "\n\nTap to open LifeLens."
    
    # Get ntfy topic URL for this patient
    from lifelens.config import NTFY_TOPIC_URL
    patient_topic = NTFY_TOPIC_URL.replace("lifelens-caregiver-alerts", 
                                            f"lifelens-med-{patient_id}")
    
    # Send ntfy notification
    try:
        # Send to patient-specific topic
        send_success = send_ntfy(
            title=title,
            body=message,
            priority="high",
            tags="pill,alarm"
        )
        
        if not send_success:
            logger.error(f"Failed to send ntfy notification for {medication_name}")
            return False
        
        # Log reminder to Qdrant
        _log_reminder(client, dose_info)
        
        logger.info(f"Sent medication reminder for {medication_name} to patient {patient_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending medication reminder: {e}")
        return False


def _log_reminder(client: QdrantClient, dose_info: Dict):
    """
    Logs reminder delivery to Qdrant for audit trail.
    """
    try:
        now = datetime.now()
        log_payload = {
            "patient_id": dose_info.get("patient_id"),
            "type": "medication_reminder_sent",
            "medication_id": dose_info.get("medication_id"),
            "medication_name": dose_info.get("medication_name"),
            "dose_time": dose_info.get("scheduled_time"),
            "reminder_date": now.date().isoformat(),
            "timestamp": now.timestamp(),
            "timestamp_iso": now.isoformat(),
            "agent": "medication_reminder"
        }
        
        # Generate embedding
        log_text = f"Medication reminder sent for {dose_info.get('medication_name')} at {dose_info.get('scheduled_time')}"
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
        
        logger.info(f"Logged reminder for {dose_info.get('medication_id')}")
        
    except Exception as e:
        logger.warning(f"Failed to log reminder: {e}")


def create_in_app_reminder(dose_info: Dict) -> Dict:
    """
    Creates an in-app reminder banner data structure.
    
    Args:
        dose_info: Dictionary containing dose details
        
    Returns:
        Dictionary with reminder banner information
    """
    return {
        "type": "medication_reminder",
        "medication_id": dose_info.get("medication_id"),
        "medication_name": dose_info.get("medication_name"),
        "dosage": dose_info.get("dosage"),
        "scheduled_time": dose_info.get("scheduled_time"),
        "notes": dose_info.get("notes", ""),
        "created_at": datetime.now().isoformat(),
        "priority": "high",
        "icon": "💊"
    }


def send_batch_reminders(client: QdrantClient, doses: List[Dict]) -> Dict[str, int]:
    """
    Sends reminders for multiple doses.
    
    Args:
        client: Qdrant client instance
        doses: List of dose information dictionaries
        
    Returns:
        Dictionary with success and failure counts
    """
    results = {
        "sent": 0,
        "failed": 0,
        "total": len(doses)
    }
    
    for dose in doses:
        success = send_medication_reminder(client, dose)
        if success:
            results["sent"] += 1
        else:
            results["failed"] += 1
    
    logger.info(f"Batch reminder results: {results}")
    return results


def send_missed_dose_alert(client: QdrantClient, patient_id: str, 
                          missed_doses: List[Dict]) -> bool:
    """
    Sends alert to caretaker about missed doses.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        missed_doses: List of missed dose information
        
    Returns:
        True if successful, False otherwise
    """
    if not missed_doses:
        return False
    
    # Create alert message
    title = "Missed Medication Alert"
    
    if len(missed_doses) == 1:
        dose = missed_doses[0]
        message = f"Patient {patient_id} missed: {dose['medication_name']} {dose['dosage']} at {dose['scheduled_time']}"
    else:
        message = f"Patient {patient_id} has {len(missed_doses)} missed doses:\n"
        for dose in missed_doses[:3]:  # Show first 3
            message += f"\n• {dose['medication_name']} at {dose['scheduled_time']}"
        
        if len(missed_doses) > 3:
            message += f"\n\n...and {len(missed_doses) - 3} more"
    
    message += "\n\nPlease check on the patient."
    
    try:
        # Send to caretaker topic
        send_success = send_ntfy(
            title=title,
            body=message,
            priority="urgent",
            tags="warning,pill"
        )
        
        if send_success:
            # Log alert
            _log_missed_dose_alert(client, patient_id, missed_doses)
            
        return send_success
        
    except Exception as e:
        logger.error(f"Error sending missed dose alert: {e}")
        return False


def _log_missed_dose_alert(client: QdrantClient, patient_id: str, 
                           missed_doses: List[Dict]):
    """
    Logs missed dose alert to Qdrant.
    """
    try:
        now = datetime.now()
        log_payload = {
            "patient_id": patient_id,
            "type": "missed_dose_alert",
            "missed_count": len(missed_doses),
            "missed_medications": [d["medication_name"] for d in missed_doses],
            "timestamp": now.timestamp(),
            "timestamp_iso": now.isoformat(),
            "agent": "medication_reminder"
        }
        
        # Generate embedding
        log_text = f"Missed dose alert for patient {patient_id}: {len(missed_doses)} doses missed"
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
        
        logger.info(f"Logged missed dose alert for patient {patient_id}")
        
    except Exception as e:
        logger.warning(f"Failed to log missed dose alert: {e}")
