"""
Notifications Module - ntfy Wrapper

Wrapper for existing ntfy notification logic.
Provides unified interface for trigger notifications.
"""

import logging
from typing import Dict
from lifelens.utils.ntfy_notifications import send_ntfy as _send_ntfy_base

logger = logging.getLogger(__name__)


def send_ntfy(message: str, priority: str = "default", patient_id: str = None, 
              title: str = "LifeLens Alert") -> bool:
    """
    Sends ntfy notification.
    
    Args:
        message: Notification message
        priority: Priority level (urgent, high, default, low)
        patient_id: Patient identifier (for logging)
        title: Notification title
        
    Returns:
        True if successful, False otherwise
    """
    
    try:
        # Map priority to ntfy format
        priority_map = {
            "urgent": 5,
            "high": 4,
            "medium": 3,
            "default": 3,
            "low": 2
        }
        
        ntfy_priority = priority_map.get(priority.lower(), 3)
        
        # Use existing send_ntfy function
        success = _send_ntfy_base(
            title=title,
            body=message,
            priority=priority
        )
        
        if success:
            logger.info(f"Sent ntfy notification for patient {patient_id}: {message[:50]}...")
        else:
            logger.warning(f"Failed to send ntfy notification")
        
        return success
        
    except Exception as e:
        logger.error(f"ntfy notification error: {e}")
        return False


def format_trigger_message(trigger: Dict) -> str:
    """
    Formats trigger dictionary into ntfy message.
    
    Args:
        trigger: Trigger dictionary
        
    Returns:
        Formatted message string
    """
    
    message = trigger.get("message", "LifeLens notification")
    trigger_type = trigger.get("type", "unknown")
    
    # Add emoji based on type
    emoji_map = {
        "memory_gap": "⏰",
        "photo_gap": "📸",
        "mood_trend": "😔",
        "untagged_people": "👤",
        "anniversary": "🎉",
        "data_request": "💡",
        "capture_suggestion": "📷"
    }
    
    emoji = emoji_map.get(trigger_type, "🔔")
    
    return f"{emoji} {message}"
