"""
Medication Critic Agent

Reviews adherence analytics and determines if a caretaker alert is warranted.
Gates alerts to prevent alert fatigue.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from qdrant_client import QdrantClient
from qdrant_client.http import models
from groq import Groq
from lifelens.config import GROQ_API_KEY

logger = logging.getLogger(__name__)


def evaluate_alert_need(client: QdrantClient, patient_id: str, 
                       adherence_insight: Dict) -> str:
    """
    Evaluates if a caretaker alert should be sent based on adherence data.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        adherence_insight: Adherence analysis results
        
    Returns:
        Verdict: "ALERT", "MONITOR", or "IGNORE"
    """
    logger.info(f"Evaluating alert need for patient {patient_id}")
    
    # Extract key metrics
    metrics = adherence_insight.get("metrics", {})
    streaks = adherence_insight.get("streaks", {})
    timing = adherence_insight.get("timing_analysis", {})
    
    missed_rate = metrics.get("missed_rate", 0)
    current_streak = streaks.get("current_missed_streak", 0)
    total_doses = metrics.get("total_doses", 0)
    
    # Check recent alert history to avoid alert fatigue
    recent_alerts = _get_recent_alerts(client, patient_id, hours=48)
    
    # Critical thresholds
    critical_streak = current_streak >= 3
    high_missed_rate = missed_rate > 0.5
    moderate_concerns = current_streak >= 2 or (missed_rate > 0.3 and total_doses > 5)
    
    # Decision logic with alert fatigue prevention
    if critical_streak or high_missed_rate:
        # Check if we already alerted recently
        if len(recent_alerts) >= 2:
            logger.info("Alert fatigue prevention: too many recent alerts")
            return "MONITOR"
        return "ALERT"
    
    elif moderate_concerns:
        if len(recent_alerts) >= 1:
            return "MONITOR"
        return "ALERT"
    
    else:
        return "IGNORE"


def generate_alert_decision(client: QdrantClient, patient_id: str, 
                           adherence_insight: Dict) -> Dict:
    """
    Generates a comprehensive alert decision with reasoning.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        adherence_insight: Adherence analysis results
        
    Returns:
        Dictionary with verdict, reasoning, and recommended action
    """
    verdict = evaluate_alert_need(client, patient_id, adherence_insight)
    
    # Get additional context
    recent_reminders = _get_recent_reminders(client, patient_id)
    
    # Use LLM to generate reasoning
    reasoning = _generate_reasoning(adherence_insight, recent_reminders, verdict)
    
    # Determine recommended action
    action = _recommend_action(verdict, adherence_insight)
    
    decision = {
        "patient_id": patient_id,
        "verdict": verdict,
        "reasoning": reasoning,
        "recommended_action": action,
        "timestamp": datetime.now().isoformat(),
        "adherence_summary": adherence_insight.get("summary", ""),
        "metrics": adherence_insight.get("metrics", {})
    }
    
    logger.info(f"Alert decision for {patient_id}: {verdict}")
    return decision


def _get_recent_alerts(client: QdrantClient, patient_id: str, 
                      hours: int = 48) -> List[Dict]:
    """
    Retrieves recent medication alerts for the patient.
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.timestamp()
        
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
                        match=models.MatchValue(value="missed_dose_alert")
                    )
                ]
            ),
            limit=10
        )[0]
        
        # Filter by time manually since lifelens_memory may use ISO timestamps
        recent = []
        for point in results:
            try:
                ts_str = point.payload.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str).timestamp()
                    if ts >= cutoff_timestamp:
                        recent.append(point.payload)
            except:
                pass
        
        return recent
        
    except Exception as e:
        logger.error(f"Error retrieving recent alerts: {e}")
        return []


def _get_recent_reminders(client: QdrantClient, patient_id: str) -> List[Dict]:
    """
    Retrieves recent medication reminders sent to the patient.
    """
    try:
        cutoff_time = datetime.now() - timedelta(days=3)
        cutoff_timestamp = cutoff_time.timestamp()
        
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
                    )
                ]
            ),
            limit=20
        )[0]
        
        # Filter by time manually
        recent = []
        for point in results:
            try:
                ts_str = point.payload.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str).timestamp()
                    if ts >= cutoff_timestamp:
                        recent.append(point.payload)
            except:
                pass
        
        return recent
        
    except Exception as e:
        logger.error(f"Error retrieving recent reminders: {e}")
        return []


def _generate_reasoning(adherence_insight: Dict, recent_reminders: List[Dict], 
                       verdict: str) -> str:
    """
    Uses LLM to generate human-readable reasoning for the decision.
    """
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        metrics = adherence_insight.get("metrics", {})
        streaks = adherence_insight.get("streaks", {})
        summary = adherence_insight.get("summary", "No summary available")
        
        prompt = f"""You are a medication adherence analyst. Review this data and explain why the verdict is '{verdict}'.

Adherence Summary: {summary}

Metrics:
- Adherence Rate: {metrics.get('adherence_rate', 0)*100:.0f}%
- Missed Rate: {metrics.get('missed_rate', 0)*100:.0f}%
- Current Missed Streak: {streaks.get('current_missed_streak', 0)}
- Total Doses Tracked: {metrics.get('total_doses', 0)}

Recent Reminders Sent: {len(recent_reminders)}

Provide a 1-2 sentence explanation for why this verdict was chosen."""
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error generating reasoning: {e}")
        return f"Verdict: {verdict} based on adherence metrics."


def _recommend_action(verdict: str, adherence_insight: Dict) -> str:
    """
    Recommends specific action based on verdict.
    """
    if verdict == "ALERT":
        return "Contact patient immediately to check on their wellbeing and medication status."
    elif verdict == "MONITOR":
        return "Continue monitoring adherence. Consider checking in with patient within 24 hours."
    else:
        return "No immediate action required. Continue regular monitoring."


def should_send_immediate_alert(adherence_insight: Dict) -> bool:
    """
    Determines if an immediate alert should be sent (bypassing normal scheduling).
    
    Args:
        adherence_insight: Adherence analysis results
        
    Returns:
        True if immediate alert needed, False otherwise
    """
    streaks = adherence_insight.get("streaks", {})
    current_streak = streaks.get("current_missed_streak", 0)
    
    # Immediate alert for 4+ consecutive misses
    if current_streak >= 4:
        return True
    
    # Check for critical medications (could be enhanced)
    metrics = adherence_insight.get("metrics", {})
    if metrics.get("missed_rate", 0) > 0.8 and metrics.get("total_doses", 0) >= 5:
        return True
    
    return False


def evaluate_and_alert(client: QdrantClient, patient_id: str, 
                      adherence_insight: Dict) -> Optional[Dict]:
    """
    Evaluates adherence and sends alert if needed.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        adherence_insight: Adherence analysis results
        
    Returns:
        Alert decision dictionary if alert sent, None otherwise
    """
    decision = generate_alert_decision(client, patient_id, adherence_insight)
    
    if decision["verdict"] == "ALERT":
        # Send alert via medication reminder agent
        from lifelens.agents.medication_reminder import send_missed_dose_alert
        from lifelens.agents.medication_scheduler import check_missed_doses
        
        missed_doses = check_missed_doses(client, patient_id)
        
        if missed_doses:
            send_missed_dose_alert(client, patient_id, missed_doses)
            logger.info(f"Sent missed dose alert for patient {patient_id}")
        
        return decision
    
    elif decision["verdict"] == "MONITOR":
        logger.info(f"Monitoring patient {patient_id} - no alert sent")
        return decision
    
    else:
        logger.info(f"No action needed for patient {patient_id}")
        return None
