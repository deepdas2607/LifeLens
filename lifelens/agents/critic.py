"""
Critic Agent - Evaluator & Safety Guard

LLM-powered agent that checks:
- Grounding (answer based on memories)
- Hallucinations
- Confidence
- Missing context
- Whether to re-retrieve

Compliant with multiagent.md Fix #6 - Standard Verdict Enum
"""

import logging
from typing import List, Dict, Optional
from groq import Groq
from lifelens.config import GROQ_API_KEY
from lifelens.utils.agent_utils import CriticVerdict, log_agent_decision

logger = logging.getLogger(__name__)


def evaluate(user_query: str, answer: str, retrieved_memories: Optional[List[Dict]], 
             session_id: Optional[str] = None, patient_id: Optional[str] = None, 
             qdrant_client=None) -> CriticVerdict:
    """
    Evaluates answer quality and safety.
    Compliant with multiagent.md Fix #6 - returns CriticVerdict enum.
    
    Args:
        user_query: Original user query
        answer: Generated answer from Executor
        retrieved_memories: Memories used to generate answer
        session_id: Session ID for logging (optional)
        patient_id: Patient ID for logging (optional)
        qdrant_client: Qdrant client for logging (optional)
        
    Returns:
        CriticVerdict enum: OK, RETRY, NOT_ENOUGH_EVIDENCE, SUGGEST_TRIGGER, or IGNORE
    """
    
    # Handle case where no memories were retrieved
    if not retrieved_memories or len(retrieved_memories) == 0:
        # Check if answer acknowledges lack of data
        if any(phrase in answer.lower() for phrase in [
            "don't have", "no memories", "couldn't find", "no relevant",
            "try uploading", "add more memories"
        ]):
            verdict = CriticVerdict.NOT_ENOUGH_EVIDENCE
        else:
            # Answer might be hallucinating
            verdict = CriticVerdict.RETRY
        
        # Log decision if possible
        if session_id and patient_id and qdrant_client:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="critic",
                    session_id=session_id,
                    verdict=verdict,
                    reasoning="No memories retrieved - evaluation based on answer content"
                )
            except Exception as e:
                logger.warning(f"Failed to log critic decision: {e}")
        
        return verdict
    
    # Build evaluation prompt
    memory_summary = _summarize_memories(retrieved_memories)
    
    system_prompt = f"""You are the Critic Agent for LifeLens, a memory assistant system.

Your job is to evaluate whether the answer is properly grounded in the retrieved memories.

USER QUERY: "{user_query}"

RETRIEVED MEMORIES:
{memory_summary}

GENERATED ANSWER: "{answer}"

EVALUATION CRITERIA:
1. GROUNDING: Does the answer only use information from the retrieved memories?
2. HALLUCINATION: Does the answer include information NOT in the memories?
3. CONFIDENCE: Is there enough information to answer confidently?
4. RELEVANCE: Are the retrieved memories relevant to the query?

VERDICT OPTIONS:
- "OK" → Answer is well-grounded and confident
- "RETRY" → Memories not relevant, need different search
- "SUGGEST_TRIGGER" → Answer is weak, suggest capturing more data
- "NOT_ENOUGH_EVIDENCE" → Not enough memories to answer
- "IGNORE" → Query doesn't require evaluation

OUTPUT FORMAT: Respond with ONLY ONE WORD - the verdict. No explanation."""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a critic agent that outputs only a single verdict word."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.1,
            max_tokens=50,
        )
        
        verdict_str = completion.choices[0].message.content.strip().upper()
        
        # Map LLM response to CriticVerdict enum
        verdict_mapping = {
            "OK": CriticVerdict.OK,
            "RETRY": CriticVerdict.RETRY,
            "RETRY_RETRIEVAL": CriticVerdict.RETRY,  # Legacy support
            "SUGGEST_TRIGGER": CriticVerdict.SUGGEST_TRIGGER,
            "NOT_ENOUGH_EVIDENCE": CriticVerdict.NOT_ENOUGH_EVIDENCE,
            "REQUEST_MORE_DATA": CriticVerdict.NOT_ENOUGH_EVIDENCE,  # Legacy support
            "IGNORE": CriticVerdict.IGNORE
        }
        
        # Find matching verdict
        verdict = None
        for key, value in verdict_mapping.items():
            if key in verdict_str:
                verdict = value
                break
        
        if not verdict:
            logger.warning(f"Unrecognized verdict from LLM: {verdict_str}, defaulting to OK")
            verdict = CriticVerdict.OK
        
        logger.info(f"Critic verdict: {verdict.value}")
        
        # Log decision if possible
        if session_id and patient_id and qdrant_client:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="critic",
                    session_id=session_id,
                    verdict=verdict,
                    reasoning=f"Evaluated query with {len(retrieved_memories)} memories",
                    metadata={
                        "memory_count": len(retrieved_memories),
                        "answer_length": len(answer)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log critic decision: {e}")
        
        return verdict
        
    except Exception as e:
        logger.error(f"Critic evaluation failed: {e}")
        # Fallback: assume OK
        return CriticVerdict.OK


def _summarize_memories(memories: List[Dict]) -> str:
    """
    Creates a concise summary of retrieved memories for evaluation.
    
    Args:
        memories: List of memory dictionaries
        
    Returns:
        Summary string
    """
    
    if not memories:
        return "No memories retrieved."
    
    summary_lines = []
    for idx, mem in enumerate(memories[:5], 1):  # Limit to top 5
        mem_type = mem.get('type', 'unknown')
        
        if mem_type == 'image':
            content = mem.get('caption', 'No caption')
        elif mem_type == 'audio':
            content = mem.get('transcript', 'No transcript')
        elif mem_type == 'text':
            content = mem.get('content', 'No content')
        elif mem_type == 'video':
            content = mem.get('analysis', 'No analysis')
        else:
            content = 'Unknown content'
        
        # Truncate long content
        if len(content) > 100:
            content = content[:100] + "..."
        
        summary_lines.append(f"{idx}. [{mem_type.upper()}] {content}")
    
    return "\n".join(summary_lines)


def evaluate_mood_alert(patient_id: str, risk_score: float, signals: Dict, 
                       recent_memories: List[Dict], visitor_correlations: Dict,
                       qdrant_client) -> str:
    """
    Evaluates mood alert before triggering caretaker notification.
    
    This is the Critic's gate-keeping function for mood alerts.
    Only ALERT verdicts will trigger notifications.
    
    Args:
        patient_id: Patient identifier
        risk_score: Calculated risk score (0-1)
        signals: Dict of computed mood signals
        recent_memories: Top recent mood events
        visitor_correlations: People-mood correlations
        qdrant_client: Qdrant client to check alert history
        
    Returns:
        Verdict: "ALERT", "MONITOR", or "IGNORE"
    """
    
    # Check prior alert history
    from datetime import datetime, timedelta
    from qdrant_client.http import models
    
    try:
        # Get alerts from last 7 days
        cutoff = datetime.now() - timedelta(days=7)
        prior_alerts = qdrant_client.scroll(
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
                            gte=cutoff.isoformat()
                        )
                    )
                ]
            ),
            limit=10
        )
        
        alert_history = [
            f"{p.payload.get('critic_verdict')} (risk: {p.payload.get('risk_score', 0):.2f})"
            for p in prior_alerts[0]
        ]
        
    except Exception as e:
        logger.warning(f"Could not retrieve alert history: {e}")
        alert_history = []
    
    # Build evaluation prompt
    memory_summary = "\n".join([
        f"- {m.get('mood', 'neutral')} at {m.get('timestamp', 'unknown')}: {m.get('source', 'text')}"
        for m in recent_memories[:5]
    ])
    
    visitor_summary = "\n".join([
        f"- {name}: {data['avg_mood']:.2f} avg mood ({data['count']} interactions)"
        for name, data in visitor_correlations.items()
    ])
    
    history_summary = "\n".join(alert_history) if alert_history else "No recent alerts"
    
    system_prompt = f"""You are the Critic Agent reviewing a mood alert for patient {patient_id}.

RISK SCORE: {risk_score:.2f} (0=low, 1=critical)

COMPUTED SIGNALS:
- Mood Slope: {signals.get('mood_slope', 0):.3f} (negative = declining)
- Negative Streak: {signals.get('negative_streak', 0)} consecutive days
- Variance Spike: {signals.get('variance_spike', 0):.2f}x baseline
- Inactivity: {signals.get('inactivity', False)}
- Recent Avg Mood: {signals.get('recent_avg_mood', 0):.2f}

RECENT MOOD EVENTS:
{memory_summary or "No recent events"}

VISITOR CORRELATIONS:
{visitor_summary or "No visitor data"}

PRIOR ALERT HISTORY (7 days):
{history_summary}

EVALUATION TASK:
Decide if this warrants a caretaker alert. Consider:
1. Is the risk score genuinely concerning?
2. Are the signals indicating real distress?
3. Is this a false positive or normal variation?
4. Have we alerted recently about similar issues?

VERDICT OPTIONS (output exactly one):
- "ALERT" → Send notification to caretaker immediately
- "MONITOR" → Log but don't notify, continue monitoring
- "IGNORE" → Not concerning, normal variation

OUTPUT: Respond with ONLY ONE WORD - your verdict. No explanation."""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a mood alert critic that outputs only: ALERT, MONITOR, or IGNORE."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.1,
            max_tokens=20,
        )
        
        verdict = completion.choices[0].message.content.strip().upper()
        
        # Validate verdict
        valid_verdicts = ["ALERT", "MONITOR", "IGNORE"]
        if verdict not in valid_verdicts:
            # Extract from response
            for valid in valid_verdicts:
                if valid in verdict:
                    verdict = valid
                    break
            else:
                # Default based on risk score
                if risk_score >= 0.75:
                    verdict = "ALERT"
                elif risk_score >= 0.5:
                    verdict = "MONITOR"
                else:
                    verdict = "IGNORE"
        
        logger.info(f"Mood alert Critic verdict: {verdict} (risk: {risk_score:.2f})")
        return verdict
        
    except Exception as e:
        logger.error(f"Mood alert evaluation failed: {e}")
        # Safe fallback: MONITOR for high risk, IGNORE for low
        return "MONITOR" if risk_score >= 0.7 else "IGNORE"
