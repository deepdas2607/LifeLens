"""
LifeLens Trigger Storage

Manages trigger persistence and history using JSON storage.
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

TRIGGER_STORAGE_FILE = "triggers.json"


def _load_all_triggers() -> Dict:
    """
    Loads all triggers from storage.
    
    Returns:
        Dictionary with patient_id as keys
    """
    if os.path.exists(TRIGGER_STORAGE_FILE):
        try:
            with open(TRIGGER_STORAGE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading triggers: {e}")
            return {}
    return {}


def _save_all_triggers(triggers: Dict) -> bool:
    """
    Saves all triggers to storage.
    
    Args:
        triggers: Dictionary with patient_id as keys
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(TRIGGER_STORAGE_FILE, "w") as f:
            json.dump(triggers, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving triggers: {e}")
        return False


def save_trigger(trigger: Dict, patient_id: str) -> str:
    """
    Saves trigger to JSON storage.
    
    Args:
        trigger: Trigger dictionary
        patient_id: Patient ID
        
    Returns:
        Trigger ID
    """
    try:
        all_triggers = _load_all_triggers()
        
        # Initialize patient triggers if not exists
        if patient_id not in all_triggers:
            all_triggers[patient_id] = []
        
        # Add unique ID and metadata
        trigger_id = str(uuid.uuid4())
        trigger["id"] = trigger_id
        trigger["patient_id"] = patient_id
        trigger["created_at"] = datetime.now().isoformat()
        trigger["dismissed"] = False
        
        # Add to patient's triggers
        all_triggers[patient_id].append(trigger)
        
        # Save to file
        _save_all_triggers(all_triggers)
        
        logger.info(f"Saved trigger {trigger_id} for patient {patient_id}")
        return trigger_id
        
    except Exception as e:
        logger.error(f"Error saving trigger: {e}")
        return ""


def load_triggers(patient_id: str, include_dismissed: bool = False) -> List[Dict]:
    """
    Loads active triggers for a patient.
    
    Args:
        patient_id: Patient ID
        include_dismissed: Whether to include dismissed triggers
        
    Returns:
        List of trigger dictionaries
    """
    try:
        all_triggers = _load_all_triggers()
        patient_triggers = all_triggers.get(patient_id, [])
        
        if include_dismissed:
            return patient_triggers
        else:
            # Filter out dismissed triggers
            return [t for t in patient_triggers if not t.get("dismissed", False)]
            
    except Exception as e:
        logger.error(f"Error loading triggers: {e}")
        return []


def dismiss_trigger(trigger_id: str, patient_id: str, action_taken: Optional[str] = None, qdrant_client=None) -> bool:
    """
    Marks trigger as dismissed and logs outcome for learning.
    
    Args:
        trigger_id: Trigger ID to dismiss
        patient_id: Patient ID
        action_taken: Optional description of action caregiver took (None if just dismissed)
        qdrant_client: Optional QdrantClient for logging to learning agent
        
    Returns:
        True if successful, False otherwise
    """
    try:
        all_triggers = _load_all_triggers()
        patient_triggers = all_triggers.get(patient_id, [])
        
        # Find and dismiss the trigger
        trigger_found = None
        for trigger in patient_triggers:
            if trigger.get("id") == trigger_id:
                trigger["dismissed"] = True
                trigger["dismissed_at"] = datetime.now().isoformat()
                if action_taken:
                    trigger["action_taken"] = action_taken
                trigger_found = trigger
                break
        
        # Save updated triggers
        all_triggers[patient_id] = patient_triggers
        _save_all_triggers(all_triggers)
        
        # Log to learning agent (if client provided)
        if trigger_found and qdrant_client:
            try:
                from lifelens.agents import log_trigger_outcome
                log_trigger_outcome(
                    client=qdrant_client,
                    trigger_id=trigger_id,
                    trigger_type=trigger_found.get("type", "unknown"),
                    sent_at=datetime.fromisoformat(trigger_found.get("created_at")).timestamp(),
                    caregiver_action=action_taken,
                    patient_id=patient_id
                )
            except Exception as e:
                logger.warning(f"Failed to log trigger outcome: {e}")
        
        logger.info(f"Dismissed trigger {trigger_id} with action: {action_taken or 'none'}")
        return True
        
    except Exception as e:
        logger.error(f"Error dismissing trigger: {e}")
        return False


def get_trigger_history(patient_id: str, days: int = 7) -> List[Dict]:
    """
    Retrieves trigger history for a patient.
    
    Args:
        patient_id: Patient ID
        days: Number of days of history to retrieve
        
    Returns:
        List of trigger dictionaries
    """
    try:
        all_triggers = load_triggers(patient_id, include_dismissed=True)
        
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        history = []
        for trigger in all_triggers:
            created_at = trigger.get("created_at")
            if created_at:
                trigger_date = datetime.fromisoformat(created_at)
                if trigger_date >= cutoff_date:
                    history.append(trigger)
        
        # Sort by creation date (newest first)
        history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting trigger history: {e}")
        return []


def clear_old_triggers(patient_id: str, days: int = 30) -> int:
    """
    Clears dismissed triggers older than specified days.
    
    Args:
        patient_id: Patient ID
        days: Age threshold in days
        
    Returns:
        Number of triggers cleared
    """
    try:
        all_triggers = _load_all_triggers()
        patient_triggers = all_triggers.get(patient_id, [])
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Keep only recent triggers or non-dismissed triggers
        original_count = len(patient_triggers)
        patient_triggers = [
            t for t in patient_triggers
            if not t.get("dismissed", False) or 
            datetime.fromisoformat(t.get("created_at", datetime.now().isoformat())) >= cutoff_date
        ]
        
        cleared_count = original_count - len(patient_triggers)
        
        # Save updated triggers
        all_triggers[patient_id] = patient_triggers
        _save_all_triggers(all_triggers)
        
        logger.info(f"Cleared {cleared_count} old triggers for patient {patient_id}")
        return cleared_count
        
    except Exception as e:
        logger.error(f"Error clearing old triggers: {e}")
        return 0
