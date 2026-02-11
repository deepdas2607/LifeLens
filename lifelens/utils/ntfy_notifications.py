"""
LifeLens ntfy Push Notifications

Handles push notifications via ntfy service for caregiver alerts.
"""

import requests
import logging
from typing import Dict, Optional
from lifelens.config import NTFY_TOPIC_URL, NTFY_MOOD_TOPIC_URL

logger = logging.getLogger(__name__)


def send_ntfy(title: str, body: str, priority: str = "default", tags: str = "bell", click_url: Optional[str] = None) -> bool:
    """
    Sends push notification to ntfy topic.
    
    Args:
        title: Notification title
        body: Notification body text
        priority: Priority level (1-5 or min, low, default, high, urgent)
        tags: Emoji tags for the notification
        click_url: Optional URL to open when notification is clicked
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Map priority levels to ntfy values
        priority_map = {
            "urgent": "5",
            "high": "4",
            "medium": "3",
            "low": "2",
            "min": "1"
        }
        
        ntfy_priority = priority_map.get(priority, "3")
        
        headers = {
            "Title": title,
            "Priority": ntfy_priority,
            "Tags": tags
        }
        
        if click_url:
            headers["Click"] = click_url
        
        # Try HTTPS first
        try:
            response = requests.post(
                NTFY_TOPIC_URL,
                data=body.encode("utf-8"),
                headers=headers,
                timeout=5
            )
        except requests.exceptions.RequestException as e:
            # Fallback to HTTP if ANY request error occurs (SSL, Connection, etc.)
            http_url = NTFY_TOPIC_URL.replace("https://", "http://")
            logger.warning(f"HTTPS failed ({e}), falling back to HTTP: {http_url}")
            try:
                response = requests.post(
                    http_url,
                    data=body.encode("utf-8"),
                    headers=headers,
                    timeout=5
                )
            except Exception as fallback_e:
                logger.error(f"Both HTTPS and HTTP fallback failed: {fallback_e}")
                return False
        
        if response.status_code == 200:
            logger.info(f"ntfy notification sent: {title}")
            return True
        else:
            logger.error(f"ntfy notification failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending ntfy notification: {e}")
        return False


def send_trigger_notification(trigger: Dict) -> bool:
    """
    Converts trigger to ntfy notification and sends it.
    
    Args:
        trigger: Trigger dictionary with type, title, message, priority
        
    Returns:
        True if successful, False otherwise
    """
    try:
        title = trigger.get("title", "LifeLens Reminder")
        message = trigger.get("message", "Check LifeLens for updates")
        priority = trigger.get("priority", "medium")
        
        # Select appropriate emoji tag based on trigger type
        tag_map = {
            "memory_gap": "bell,calendar",
            "mood_trend": "warning,heart",
            "media_gap": "camera,reminder_ribbon",
            "milestone_anniversary": "tada,calendar",
            "untagged_people": "bust_in_silhouette,label"
        }
        
        tags = tag_map.get(trigger.get("type", ""), "bell")
        
        return send_ntfy(title, message, priority, tags)
        
    except Exception as e:
        logger.error(f"Error sending trigger notification: {e}")
        return False


def schedule_daily_recap_reminder(patient_name: str = "patient") -> bool:
    """
    Schedules daily recap notification.
    
    Args:
        patient_name: Name of the patient for personalization
        
    Returns:
        True if successful, False otherwise
    """
    title = "LifeLens Daily Recap"
    message = f"Time to add today's memories for {patient_name}. Even small moments matter!"
    
    return send_ntfy(title, message, priority="medium", tags="calendar,memo")


def send_custom_notification(title: str, message: str, priority: str = "medium") -> bool:
    """
    Sends a custom notification.
    
    Args:
        title: Notification title
        message: Notification message
        priority: Priority level
        
    Returns:
        True if successful, False otherwise
    """
    return send_ntfy(title, message, priority, tags="bell")


def send_mood_alert(patient_id: str, summary: str, risk_score: float) -> bool:
    """
    Sends mood alert notification to caretaker.
    
    Uses dedicated topic format: lifelens-mood-{patient_id}
    
    Args:
        patient_id: Patient identifier
        summary: Human-readable alert summary
        risk_score: Risk score (0-1)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Determine priority based on risk score
        if risk_score >= 0.8:
            priority = "urgent"
            tags = "rotating_light,warning,heart"
            priority_num = "5"
        elif risk_score >= 0.6:
            priority = "high"
            tags = "warning,heart,medical_symbol"
            priority_num = "4"
        else:
            priority = "medium"
            tags = "thought_balloon,heart"
            priority_num = "3"
        
        # Don't use emojis in title (causes encoding errors), use emoji tags instead
        title = f"Mood Alert - Patient {patient_id}"
        
        message = f"""LifeLens detected a sustained negative mood pattern.

Summary: {summary}
Risk Level: {risk_score:.0%}

Please review recent memories and consider reaching out to the patient."""
        
        # Use mood-specific topic URL (can be patient-specific or demo topic)
        topic_url = NTFY_MOOD_TOPIC_URL
        
        headers = {
            "Title": title,
            "Priority": priority_num,
            "Tags": tags
        }
        
        # Try HTTPS first
        try:
            response = requests.post(
                topic_url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=5
            )
        except requests.exceptions.RequestException as e:
            # Fallback to HTTP
            http_url = topic_url.replace("https://", "http://")
            logger.warning(f"HTTPS failed ({e}), falling back to HTTP: {http_url}")
            response = requests.post(
                http_url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=5
            )
        
        if response.status_code == 200:
            logger.info(f"Mood alert sent for patient {patient_id} (risk: {risk_score:.2f})")
            return True
        else:
            logger.error(f"Mood alert failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending mood alert: {e}")
        return False
