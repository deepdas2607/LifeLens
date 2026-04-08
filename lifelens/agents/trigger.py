"""
Trigger Agent - Proactive System

Generates intelligent triggers based on:
- Critic verdicts
- Qdrant stats
- Inactivity patterns
- Repeated questions
- Mood trends

Compliant with multiagent.md Fix #7 - Trigger Agent Contract
"""

import logging
from typing import List, Dict, Optional, Union
from qdrant_client import QdrantClient
from lifelens.utils.trigger_agent import (
    get_patient_stats,
    detect_memory_gaps,
    detect_mood_trends,
    detect_media_gaps,
    detect_untagged_people,
    detect_milestone_anniversaries,
    get_trigger_priority
)
from lifelens.utils.agent_utils import CriticVerdict, should_trigger, log_agent_decision

logger = logging.getLogger(__name__)


def generate(critic_verdict: Union[CriticVerdict, str], patient_id: str,  
             qdrant_client: QdrantClient, session_id: Optional[str] = None,
             risk_score: Optional[float] = None) -> List[Dict]:
    """
    Generates proactive triggers based on Critic verdict and patient patterns.
    Implements multiagent.md Fix #7 - Conditional trigger firing.
    
    Args:
        critic_verdict: Verdict from Critic agent (enum or string for backward compat)
        patient_id: Patient identifier
        qdrant_client: Qdrant client instance
        session_id: Session ID for logging
        risk_score: Optional risk score for trigger threshold
        
    Returns:
        List of trigger dictionaries
    """
    
    # Convert string verdict to enum if needed (backward compatibility)
    if isinstance(critic_verdict, str):
        verdict_mapping = {
            "REQUEST_MORE_DATA": CriticVerdict.NOT_ENOUGH_EVIDENCE,
            "SUGGEST_TRIGGER": CriticVerdict.SUGGEST_TRIGGER,
            "RETRY_RETRIEVAL": CriticVerdict.RETRY,
            "ALERT": CriticVerdict.SUGGEST_TRIGGER,
            "OK": CriticVerdict.OK
        }
        verdict = verdict_mapping.get(critic_verdict, CriticVerdict.IGNORE)
    else:
        verdict = critic_verdict
    
    # GATE: Check if trigger should fire (multiagent.md Fix #7)
    if not should_trigger(verdict, risk_score, threshold=0.5):
        logger.info(f"Trigger conditions not met for verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict}")
        
        # Log decision
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="trigger",
                    session_id=session_id,
                    verdict=verdict,
                    reasoning=f"Trigger conditions not met (verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict})",
                    metadata={"risk_score": risk_score}
                )
            except Exception as e:
                logger.warning(f"Failed to log trigger decision: {e}")
        
        return []
    
    logger.info(f"Trigger conditions met for verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict}")
    
    triggers = []
    
    # 1. Verdict-based triggers
    if verdict == CriticVerdict.NOT_ENOUGH_EVIDENCE:
        triggers.append({
            "type": "data_request",
            "priority": "high",
            "message": "💡 LifeLens needs more memories to answer your questions better. Consider uploading recent photos or notes!",
            "action": "upload_prompt"
        })
    
    elif verdict == CriticVerdict.SUGGEST_TRIGGER:
        triggers.append({
            "type": "capture_suggestion",
            "priority": "medium",
            "message": "📸 Capture this moment! It might be helpful to remember later.",
            "action": "camera_prompt"
        })
    
    # 2. Risk-based triggers (from Mood Intelligence Agent)
    if risk_score and risk_score >= 0.7:
        triggers.append({
            "type": "mood_alert",
            "priority": "urgent",
            "title": "⚠️ Mood Alert Detected",
            "message": "Sustained negative mood pattern detected. Please review recent memories.",
            "action": "review_mood",
            "risk_score": risk_score
        })
    
    # 3. Pattern-based triggers (using existing trigger logic)
    try:
        stats = get_patient_stats(qdrant_client, patient_id)
        
        # Memory gap detection
        gap_trigger = detect_memory_gaps(stats)
        if gap_trigger:
            triggers.append(gap_trigger)
        
        # Mood trend detection
        mood_trigger = detect_mood_trends(stats)
        if mood_trigger:
            triggers.append(mood_trigger)
        
        # Media gap detection
        media_trigger = detect_media_gaps(stats)
        if media_trigger:
            triggers.append(media_trigger)
        
        # Untagged people detection
        untagged_trigger = detect_untagged_people(stats)
        if untagged_trigger:
            triggers.append(untagged_trigger)
        
        # Anniversary detection
        anniversary_trigger = detect_milestone_anniversaries(qdrant_client, patient_id)
        if anniversary_trigger:
            triggers.append(anniversary_trigger)
            
    except Exception as e:
        logger.error(f"Pattern-based trigger generation failed: {e}")
    
    # Assign priorities
    for trigger in triggers:
        if "priority" not in trigger:
            trigger["priority"] = get_trigger_priority(trigger.get("type", "unknown"))
    
    logger.info(f"Generated {len(triggers)} triggers for patient {patient_id}")
    
    # Log trigger decision to Qdrant (multiagent.md Fix #3)
    if session_id:
        try:
            log_agent_decision(
                client=qdrant_client,
                patient_id=patient_id,
                agent="trigger",
                session_id=session_id,
                verdict=verdict,
                reasoning=f"Generated {len(triggers)} triggers based on verdict {verdict.value if isinstance(verdict, CriticVerdict) else verdict}",
                metadata={
                    "trigger_count": len(triggers),
                    "trigger_types": [t["type"] for t in triggers],
                    "risk_score": risk_score
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log trigger decision: {e}")
    
    return triggers
