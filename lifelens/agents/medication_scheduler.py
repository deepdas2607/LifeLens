"""
Medication Scheduler Agent

Runs periodically to check for upcoming medication doses.
Generates reminder tasks for the Reminder Agent.
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def get_active_medications(client: QdrantClient, patient_id: str) -> List[Dict]:
    """
    Retrieves all active medications for a patient.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        
    Returns:
        List of active medication records
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
        
        medications = []
        current_date = datetime.now().date()
        
        for point in results:
            payload = point.payload
            start_date = datetime.fromisoformat(payload.get("start_date")).date()
            end_date_str = payload.get("end_date")
            
            # Check if medication is within active date range
            if start_date > current_date:
                continue
                
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str).date()
                if end_date < current_date:
                    continue
            
            medications.append(payload)
        
        return medications
        
    except Exception as e:
        logger.error(f"Error retrieving active medications: {e}")
        return []


def get_upcoming_doses(client: QdrantClient, patient_id: str, 
                      look_ahead_minutes: int = 10) -> List[Dict]:
    """
    Identifies medication doses due within the next X minutes.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        look_ahead_minutes: How far ahead to check (default: 10 minutes)
        
    Returns:
        List of upcoming dose reminders
    """
    medications = get_active_medications(client, patient_id)
    upcoming = []
    
    now = datetime.now()
    current_time = now.time()
    
    for med in medications:
        schedule = med.get("schedule", [])
        
        for dose_time_str in schedule:
            try:
                dose_time = datetime.strptime(dose_time_str, "%H:%M").time()
                
                # Create datetime for today's dose
                dose_datetime = datetime.combine(now.date(), dose_time)
                
                # Check if dose is within look-ahead window
                time_until_dose = (dose_datetime - now).total_seconds() / 60
                
                if 0 <= time_until_dose <= look_ahead_minutes:
                    # Check if reminder already sent for this dose today
                    if not _reminder_already_sent(client, patient_id, 
                                                  med["medication_id"], 
                                                  dose_time_str, now.date()):
                        upcoming.append({
                            "patient_id": patient_id,
                            "medication_id": med["medication_id"],
                            "medication_name": med["name"],
                            "dosage": med["dosage"],
                            "scheduled_time": dose_time_str,
                            "due_at": dose_datetime.isoformat(),
                            "notes": med.get("notes", ""),
                            "minutes_until": int(time_until_dose)
                        })
                        
            except ValueError as e:
                logger.error(f"Error parsing time {dose_time_str}: {e}")
                continue
    
    return upcoming


def _reminder_already_sent(client: QdrantClient, patient_id: str, 
                           medication_id: str, dose_time: str, 
                           date: datetime.date) -> bool:
    """
    Checks if a reminder has already been sent for this dose today.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        medication_id: Medication identifier
        dose_time: Scheduled dose time (HH:MM)
        date: Date to check
        
    Returns:
        True if reminder already sent, False otherwise
    """
    try:
        # Check in main memory collection for reminder logs
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        # Convert to Unix timestamps
        start_timestamp = start_of_day.timestamp()
        end_timestamp = end_of_day.timestamp()
        
        results = client.scroll(
            collection_name="lifelens_memory",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="medication_reminder_sent")
                    ),
                    models.FieldCondition(
                        key="medication_id",
                        match=models.MatchValue(value=medication_id)
                    ),
                    models.FieldCondition(
                        key="reminder_date",
                        match=models.MatchValue(value=date.isoformat())
                    )
                ]
            ),
            limit=10
        )[0]
        
        # Check if any result matches the dose_time
        for point in results:
            if point.payload.get("dose_time") == dose_time:
                return True
        
        return False
        
    except Exception as e:
        logger.warning(f"Error checking reminder status: {e}")
        return False  # Assume not sent if error


def get_todays_medications(client: QdrantClient, patient_id: str) -> List[Dict]:
    """
    Gets all medications scheduled for today with their status.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        
    Returns:
        List of today's medications with status
    """
    medications = get_active_medications(client, patient_id)
    today_schedule = []
    
    now = datetime.now()
    today_date = now.date()
    
    for med in medications:
        schedule = med.get("schedule", [])
        
        for dose_time_str in schedule:
            try:
                dose_time = datetime.strptime(dose_time_str, "%H:%M").time()
                dose_datetime = datetime.combine(today_date, dose_time)
                
                # Get status for this dose today
                status = _get_dose_status(client, patient_id, med["medication_id"], 
                                        dose_time_str, today_date)
                
                # Determine if overdue
                is_overdue = dose_datetime < now and status == "pending"
                
                today_schedule.append({
                    "medication_id": med["medication_id"],
                    "medication_name": med["name"],
                    "dosage": med["dosage"],
                    "scheduled_time": dose_time_str,
                    "status": status,
                    "is_overdue": is_overdue,
                    "notes": med.get("notes", "")
                })
                
            except ValueError as e:
                logger.error(f"Error parsing time {dose_time_str}: {e}")
                continue
    
    # Sort by scheduled time
    today_schedule.sort(key=lambda x: x["scheduled_time"])
    
    return today_schedule


def _get_dose_status(client: QdrantClient, patient_id: str, 
                    medication_id: str, dose_time: str, 
                    date: datetime.date) -> str:
    """
    Gets the status of a specific dose for a specific date.
    
    Returns:
        Status string: "taken", "skipped", "missed", or "pending"
    """
    try:
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        # Convert to Unix timestamps for Range query
        start_timestamp = start_of_day.timestamp()
        end_timestamp = end_of_day.timestamp()
        
        results = client.scroll(
            collection_name="medication_events",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="medication_id",
                        match=models.MatchValue(value=medication_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(
                            gte=start_timestamp,
                            lte=end_timestamp
                        )
                    )
                ]
            ),
            limit=100
        )[0]
        
        # Check if any event matches the dose_time
        for point in results:
            event_dose_time = point.payload.get("dose_time", "")
            if event_dose_time == dose_time:
                return point.payload.get("status", "pending")
        
        return "pending"
        
    except Exception as e:
        logger.error(f"Error getting dose status: {e}")
        return "pending"


def check_missed_doses(client: QdrantClient, patient_id: str) -> List[Dict]:
    """
    Identifies doses that should have been taken but weren't marked.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        
    Returns:
        List of missed doses
    """
    today_meds = get_todays_medications(client, patient_id)
    missed = []
    
    for dose in today_meds:
        if dose["is_overdue"] and dose["status"] == "pending":
            missed.append(dose)
    
    return missed
