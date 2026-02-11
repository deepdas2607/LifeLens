"""
Mood Intelligence Agent - Longitudinal Emotional Monitoring

Analyzes multi-week mood history, detects anomalies, correlates events,
assesses risk, and triggers caretaker alerts through Critic review.

This is a production agent that queries real data from Qdrant, not mock pipelines.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http import models
from groq import Groq
from lifelens.config import GROQ_API_KEY
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict, should_trigger
import uuid

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _convert_mood_to_score(mood: str) -> float:
    """
    Maps mood string to numerical score.
    Positive moods: positive scores
    Negative moods: negative scores
    Neutral: 0
    """
    mood_map = {
        "happy": 0.8,
        "excited": 0.9,
        "content": 0.6,
        "calm": 0.5,
        "neutral": 0.0,
        "anxious": -0.4,
        "confused": -0.3,
        "sad": -0.6,
        "angry": -0.7,
        "depressed": -0.9,
        "frustrated": -0.5,
        "lonely": -0.6,
        "worried": -0.5
    }
    
    return mood_map.get(mood.lower(), 0.0)


def _calculate_mood_slope(mood_scores: List[Tuple[datetime, float]]) -> float:
    """
    Calculates trend slope using linear regression on mood scores over time.
    
    Returns:
        Slope value: negative = declining mood, positive = improving mood
    """
    if len(mood_scores) < 2:
        return 0.0
    
    # Convert to numpy arrays
    timestamps = np.array([ts.timestamp() for ts, _ in mood_scores])
    scores = np.array([score for _, score in mood_scores])
    
    # Normalize timestamps to days from start
    timestamps = (timestamps - timestamps[0]) / 86400.0  # seconds to days
    
    # Linear regression: y = mx + b
    n = len(timestamps)
    x_mean = np.mean(timestamps)
    y_mean = np.mean(scores)
    
    numerator = np.sum((timestamps - x_mean) * (scores - y_mean))
    denominator = np.sum((timestamps - x_mean) ** 2)
    
    if denominator == 0:
        return 0.0
    
    slope = numerator / denominator
    return float(slope)


def _detect_negative_streak(mood_scores: List[Tuple[datetime, float]]) -> int:
    """
    Detects consecutive days with negative mood.
    
    Returns:
        Length of current negative streak (0 if none or positive)
    """
    if not mood_scores:
        return 0
    
    # Group by date
    daily_moods = {}
    for ts, score in mood_scores:
        date = ts.date()
        if date not in daily_moods:
            daily_moods[date] = []
        daily_moods[date].append(score)
    
    # Calculate daily averages
    daily_avgs = {date: np.mean(scores) for date, scores in daily_moods.items()}
    
    # Sort by date (most recent first)
    sorted_dates = sorted(daily_avgs.keys(), reverse=True)
    
    # Count consecutive negative days from most recent
    streak = 0
    for date in sorted_dates:
        if daily_avgs[date] < -0.2:  # threshold for "negative"
            streak += 1
        else:
            break
    
    return streak


def _calculate_variance_spike(mood_scores: List[Tuple[datetime, float]], 
                              baseline_scores: List[Tuple[datetime, float]]) -> float:
    """
    Detects if recent mood variance is significantly higher than baseline.
    
    Returns:
        Ratio of recent std-dev to baseline std-dev (>1.5 = spike)
    """
    if len(mood_scores) < 3 or len(baseline_scores) < 3:
        return 0.0
    
    recent_std = np.std([score for _, score in mood_scores])
    baseline_std = np.std([score for _, score in baseline_scores])
    
    if baseline_std == 0:
        return 0.0
    
    return float(recent_std / baseline_std)


def _check_inactivity(qdrant_client: QdrantClient, patient_id: str) -> bool:
    """
    Checks if patient has been inactive (no uploads) for 48+ hours.
    
    Returns:
        True if inactive, False otherwise
    """
    try:
        # Try mood_events first, fallback to memory_vectors
        for collection in ["mood_events", "memory_vectors"]:
            try:
                results = qdrant_client.scroll(
                    collection_name=collection,
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
                )
                
                if results and results[0]:
                    latest_memory = results[0][0].payload
                    ts_val = latest_memory.get("timestamp")
                    if isinstance(ts_val, str):
                        latest_ts = datetime.fromisoformat(ts_val.replace("Z", "+00:00")).replace(tzinfo=None)
                    else:
                        latest_ts = datetime.utcfromtimestamp(ts_val)
                    hours_since = (datetime.utcnow() - latest_ts).total_seconds() / 3600
                    return hours_since >= 48
            except Exception:
                continue
        
        return True  # No memories in any collection
        
    except Exception as e:
        logger.warning(f"Could not check inactivity: {e}")
        return False


def _get_visitor_correlations(qdrant_client: QdrantClient, patient_id: str, 
                              days: int = 7) -> Dict[str, Dict]:
    """
    Analyzes mood patterns when specific people are present.
    
    Returns:
        Dict mapping person name to mood statistics
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        results = qdrant_client.scroll(
            collection_name="mood_events",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.DatetimeRange(
                            gte=cutoff.isoformat() + "Z"
                        )
                    )
                ]
            ),
            limit=1000
        )
        
        # Group by people
        person_moods = {}
        
        for record in results[0]:
            payload = record.payload
            people = payload.get("people", [])
            mood_score = payload.get("mood_score", 0)
            
            for person in people:
                if person not in person_moods:
                    person_moods[person] = []
                person_moods[person].append(mood_score)
        
        # Calculate statistics
        correlations = {}
        for person, scores in person_moods.items():
            if len(scores) >= 2:
                correlations[person] = {
                    "avg_mood": float(np.mean(scores)),
                    "count": len(scores),
                    "trend": "positive" if np.mean(scores) > 0 else "negative"
                }
        
        return correlations
        
    except Exception as e:
        logger.error(f"Error calculating visitor correlations: {e}")
        return {}


def _get_mood_data(qdrant_client: QdrantClient, patient_id: str, 
                   days: int) -> List[Tuple[datetime, float, Dict]]:
    """
    Retrieves mood events from Qdrant for specified time window.
    
    Returns:
        List of (timestamp, mood_score, full_payload) tuples, sorted chronologically
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        results = qdrant_client.scroll(
            collection_name="mood_events",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.DatetimeRange(
                            gte=cutoff.isoformat() + "Z"
                        )
                    )
                ]
            ),
            limit=1000
        )
        
        mood_data = []
        for record in results[0]:
            payload = record.payload
            ts_str = payload["timestamp"]
            # Parse timestamp properly
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
            score = payload.get("mood_score", 0)
            mood_data.append((ts, score, payload))
        
        # Sort chronologically (oldest first) for proper trend analysis
        mood_data.sort(key=lambda x: x[0])
        
        return mood_data
        
    except Exception as e:
        logger.error(f"Error retrieving mood data: {e}")
        return []


def calculate_risk_score(patient_id: str, qdrant_client: QdrantClient) -> Dict:
    """
    Computes comprehensive mood risk score based on multiple signals.
    
    Returns:
        Dict containing risk_score, signals, and analysis data
    """
    try:
        # Retrieve mood data
        recent_data = _get_mood_data(qdrant_client, patient_id, days=7)
        baseline_data = _get_mood_data(qdrant_client, patient_id, days=30)
        
        if not recent_data:
            return {
                "risk_score": 0.0,
                "insufficient_data": True,
                "message": "No mood data available for analysis"
            }
        
        # Extract mood scores
        recent_scores = [(ts, score) for ts, score, _ in recent_data]
        baseline_scores = [(ts, score) for ts, score, _ in baseline_data]
        
        # Calculate signals
        mood_slope = _calculate_mood_slope(recent_scores)
        negative_streak = _detect_negative_streak(recent_scores)
        variance_spike = _calculate_variance_spike(recent_scores, baseline_scores)
        inactivity = _check_inactivity(qdrant_client, patient_id)
        visitor_correlations = _get_visitor_correlations(qdrant_client, patient_id, days=7)
        
        # Normalize signals to [0, 1]
        # Negative trend: more negative slope = higher risk
        # Scale by 7 to make -0.1 per day = 0.7 risk (sensitive to declining mood)
        normalized_trend = max(0, min(1, -mood_slope * 7))
        
        # Streak factor: 3+ days = significant risk
        streak_factor = min(1.0, negative_streak / 5.0)
        
        # Anomaly score: variance spike > 1.5 = risk
        anomaly_score = min(1.0, max(0, variance_spike - 1.0) / 1.0)
        
        # Inactivity flag
        inactivity_flag = 1.0 if inactivity else 0.0
        
        # Recent mood average (needed for negativity factor)
        recent_avg = np.mean([score for _, score in recent_scores])
        
        # Recent mood average negativity factor (how deeply negative)
        # -0.5 or worse = high concern (more sensitive)
        negativity_factor = max(0, min(1, (-recent_avg - 0.3) / 0.6))  # Scale -0.3 to -0.9 → 0 to 1
        
        # Compute weighted risk score with emphasis on trend + duration + depth
        risk_score = (
            0.35 * normalized_trend +      # Trend direction (increased)
            0.35 * streak_factor +          # Duration of negativity (increased)
            0.20 * negativity_factor +      # Depth of negativity (maintained)
            0.05 * anomaly_score +          # Variance spike (reduced)
            0.05 * inactivity_flag          # Engagement level (reduced)
        )
        
        return {
            "risk_score": float(risk_score),
            "signals": {
                "mood_slope": float(mood_slope),
                "negative_streak": negative_streak,
                "variance_spike": float(variance_spike),
                "inactivity": inactivity,
                "recent_avg_mood": float(recent_avg),
                "normalized_trend": float(normalized_trend),
                "streak_factor": float(streak_factor),
                "anomaly_score": float(anomaly_score)
            },
            "visitor_correlations": visitor_correlations,
            "data_points": len(recent_data),
            "insufficient_data": False
        }
        
    except Exception as e:
        logger.error(f"Error calculating risk score: {e}")
        return {
            "risk_score": 0.0,
            "error": str(e)
        }


def run_mood_analysis(patient_id: str, qdrant_client: QdrantClient, 
                     trigger_alerts: bool = True, session_id: Optional[str] = None) -> Optional[Dict]:
    """
    Main entry point for Mood Intelligence Agent.
    
    Runs analysis, calculates risk, routes through Critic, and triggers alerts.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        patient_id: Patient identifier
        qdrant_client: Qdrant client instance
        trigger_alerts: If True, will create alerts and send notifications
        session_id: Session ID for logging
        
    Returns:
        Analysis result dict with risk score, verdict, and alert status
    """
    try:
        logger.info(f"Running mood analysis for patient {patient_id}")
        
        # Calculate risk score
        analysis = calculate_risk_score(patient_id, qdrant_client)
        
        if analysis.get("insufficient_data"):
            logger.info(f"Insufficient mood data for patient {patient_id}")
            
            # Log insufficient data decision
            if session_id:
                try:
                    log_agent_decision(
                        client=qdrant_client,
                        patient_id=patient_id,
                        agent="mood_agent",
                        session_id=session_id,
                        verdict=CriticVerdict.IGNORE,
                        reasoning="Insufficient mood data for analysis",
                        metadata={"data_points": analysis.get("data_points", 0)}
                    )
                except Exception as e:
                    logger.warning(f"Failed to log mood decision: {e}")
            
            return analysis
        
        risk_score = analysis["risk_score"]
        logger.info(f"Risk score calculated: {risk_score:.2f}")
        
        # Only proceed if risk is significant
        if risk_score < 0.5:
            logger.info(f"Risk score {risk_score:.2f} below threshold, no alert needed")
            
            # Log low-risk decision
            if session_id:
                try:
                    log_agent_decision(
                        client=qdrant_client,
                        patient_id=patient_id,
                        agent="mood_agent",
                        session_id=session_id,
                        verdict=CriticVerdict.OK,
                        reasoning=f"Risk score {risk_score:.2f} below alert threshold",
                        metadata={"risk_score": risk_score, "signals": analysis.get("signals", {})}
                    )
                except Exception as e:
                    logger.warning(f"Failed to log mood decision: {e}")
            
            return {**analysis, "verdict": CriticVerdict.OK, "alert_needed": False}
        
        # Route through Critic Agent for review
        from lifelens.agents.critic import evaluate_mood_alert
        
        recent_data = _get_mood_data(qdrant_client, patient_id, days=7)
        top_memories = [payload for _, _, payload in recent_data[:3]]
        
        verdict = evaluate_mood_alert(
            patient_id=patient_id,
            risk_score=risk_score,
            signals=analysis["signals"],
            recent_memories=top_memories,
            visitor_correlations=analysis["visitor_correlations"],
            qdrant_client=qdrant_client
        )
        
        logger.info(f"Critic verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict}")
        
        # Convert string verdict to enum if needed (backward compatibility)
        if isinstance(verdict, str):
            verdict_mapping = {
                "ALERT": CriticVerdict.SUGGEST_TRIGGER,
                "IGNORE": CriticVerdict.IGNORE,
                "OK": CriticVerdict.OK
            }
            verdict = verdict_mapping.get(verdict, CriticVerdict.OK)
        
        # Generate summary
        summary = _generate_alert_summary(analysis, verdict)
        
        # Store alert decision in Qdrant
        alert_id = str(uuid.uuid4())
        alert_payload = {
            "alert_id": alert_id,
            "patient_id": patient_id,
            "timestamp": datetime.utcnow().timestamp(),  # Use Unix timestamp
            "risk_score": risk_score,
            "critic_verdict": verdict.value if isinstance(verdict, CriticVerdict) else verdict,
            "summary": summary,
            "signals": analysis["signals"],
            "notified": False
        }
        
        # Store in mood_alerts collection
        qdrant_client.upsert(
            collection_name="mood_alerts",
            points=[
                models.PointStruct(
                    id=alert_id,
                    vector=[0],  # Minimal vector
                    payload=alert_payload
                )
            ]
        )
        
        # Trigger notification using should_trigger() gate (multiagent.md Fix #7)
        if trigger_alerts and should_trigger(verdict, risk_score):
            # Check anti-spam: max 1 alert per 24h
            if _check_alert_spam(qdrant_client, patient_id):
                logger.info("Alert suppressed due to recent notification (anti-spam)")
                alert_payload["notified"] = False
                alert_payload["spam_suppressed"] = True
            else:
                # Send notification
                from lifelens.utils.ntfy_notifications import send_mood_alert
                notified = send_mood_alert(patient_id, summary, risk_score)
                alert_payload["notified"] = notified
        
        # Log mood analysis decision (multiagent.md Fix #3)
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="mood_agent",
                    session_id=session_id,
                    verdict=verdict,
                    reasoning=f"Mood analysis completed with risk score {risk_score:.2f} and verdict {verdict.value}",
                    metadata={
                        "risk_score": risk_score,
                        "alert_id": alert_id,
                        "alert_needed": should_trigger(verdict, risk_score),
                        "notified": alert_payload.get("notified", False),
                        "signals": analysis["signals"]
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log mood decision: {e}")
        
        return {
            **analysis,
            "verdict": verdict.value if isinstance(verdict, CriticVerdict) else verdict,
            "summary": summary,
            "alert_id": alert_id,
            "alert_needed": should_trigger(verdict, risk_score),
            "notified": alert_payload.get("notified", False)
        }
        
    except Exception as e:
        logger.error(f"Error in mood analysis: {e}")
        return {"error": str(e), "risk_score": 0.0}


def _generate_alert_summary(analysis: Dict, verdict) -> str:
    """
    Generates human-readable summary of mood alert.
    
    Args:
        analysis: Analysis dict with signals
        verdict: CriticVerdict enum or string verdict
    """
    signals = analysis["signals"]
    streak = signals.get("negative_streak", 0)
    slope = signals.get("mood_slope", 0)
    inactivity = signals.get("inactivity", False)
    
    summary_parts = []
    
    if streak >= 3:
        summary_parts.append(f"{streak}-day negative mood streak")
    
    if slope < -0.1:
        summary_parts.append("declining mood trend")
    
    if inactivity:
        summary_parts.append("48+ hour inactivity")
    
    if not summary_parts:
        summary_parts.append("elevated mood risk detected")
    
    return " + ".join(summary_parts)


def _check_alert_spam(qdrant_client: QdrantClient, patient_id: str) -> bool:
    """
    Checks if an alert was sent in the last 24 hours.
    
    Returns:
        True if recent alert exists (should suppress), False otherwise
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        results = qdrant_client.scroll(
            collection_name="mood_alerts",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.DatetimeRange(
                            gte=cutoff.isoformat() + "Z"
                        )
                    ),
                    models.FieldCondition(
                        key="notified",
                        match=models.MatchValue(value=True)
                    )
                ]
            ),
            limit=1
        )
        
        return len(results[0]) > 0
        
    except Exception as e:
        logger.error(f"Error checking alert spam: {e}")
        return False  # Default to allowing alert if check fails


def store_mood_feedback(qdrant_client: QdrantClient, alert_id: str, 
                       patient_id: str, action: str, notes: str = "") -> bool:
    """
    Stores caregiver feedback for learning loop.
    
    Args:
        alert_id: ID of the alert being reviewed
        patient_id: Patient identifier
        action: "acknowledged", "dismissed", "corrective_action"
        notes: Optional caregiver notes
        
    Returns:
        True if stored successfully
    """
    try:
        feedback_id = str(uuid.uuid4())
        
        feedback_payload = {
            "feedback_id": feedback_id,
            "alert_id": alert_id,
            "patient_id": patient_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "notes": notes
        }
        
        qdrant_client.upsert(
            collection_name="mood_feedback",
            points=[
                models.PointStruct(
                    id=feedback_id,
                    vector=[0],
                    payload=feedback_payload
                )
            ]
        )
        
        logger.info(f"Mood feedback stored: {action} for alert {alert_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing mood feedback: {e}")
        return False
