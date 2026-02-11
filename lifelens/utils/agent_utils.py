"""
Agent Utilities - Multi-Agent System Compliance

Provides standard utilities for agent decision logging, verdict enums,
and plan schemas as defined in multiagent.md specification.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from qdrant_client import QdrantClient
from qdrant_client.http import models
import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY, VECTOR_SIZE

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)


class CriticVerdict(Enum):
    """
    Standard verdict enum for all critic agents.
    As defined in multiagent.md Fix #6.
    """
    OK = "OK"
    RETRY = "RETRY"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"
    SUGGEST_TRIGGER = "SUGGEST_TRIGGER"
    IGNORE = "IGNORE"


class Intent(Enum):
    """Standard intent types for planner schema."""
    MEMORY_RECALL = "memory_recall"
    INGESTION = "ingestion"
    ANALYTICS = "analytics"
    SUMMARY = "summary"
    TRIGGER_SCAN = "trigger_scan"
    MEDICATION = "medication"
    MOOD = "mood"


def create_standard_plan(
    intent: Intent,
    needs_retrieval: bool = True,
    temporal_scope: str = "last_week",
    entities: List[str] = None,
    modalities: List[str] = None,
    confidence_threshold: float = 0.75,
    fallback: str = "ask_caretaker",
    trigger_if_missing: bool = False,
    max_retries: int = 2,
    **extra_fields
) -> Dict:
    """
    Creates a standard plan following multiagent.md schema (Fix #1).
    
    Args:
        intent: Primary intent of the query
        needs_retrieval: Whether retrieval is needed
        temporal_scope: Time range for retrieval
        entities: List of entities to search for
        modalities: List of modalities required
        confidence_threshold: Minimum confidence for results
        fallback: Fallback strategy if plan fails
        trigger_if_missing: Whether to trigger if data missing
        max_retries: Maximum retry attempts
        **extra_fields: Additional agent-specific fields
        
    Returns:
        Standard plan dictionary
    """
    plan = {
        "intent": intent.value,
        "needs_retrieval": needs_retrieval,
        "temporal_scope": temporal_scope,
        "entities": entities or [],
        "modalities": modalities or [],
        "confidence_threshold": confidence_threshold,
        "fallback": fallback,
        "trigger_if_missing": trigger_if_missing,
        "max_retries": max_retries
    }
    
    # Add any extra agent-specific fields
    plan.update(extra_fields)
    
    return plan


def log_agent_decision(
    client: QdrantClient,
    patient_id: str,
    agent: str,
    session_id: str,
    plan: Optional[Dict] = None,
    verdict: Optional[CriticVerdict] = None,
    attempt: int = 0,
    reasoning: str = "",
    metadata: Optional[Dict] = None
) -> str:
    """
    Logs agent decision to Qdrant agent_decisions collection.
    As defined in multiagent.md Fix #3.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        agent: Agent name (planner, critic, retriever, etc.)
        session_id: Unique session identifier for this query flow
        plan: The plan dictionary (if applicable)
        verdict: Critic verdict (if applicable)
        attempt: Retry attempt number (0-based)
        reasoning: Human-readable reasoning
        metadata: Additional metadata
        
    Returns:
        Decision ID (UUID)
    """
    try:
        decision_id = str(uuid.uuid4())
        now = datetime.now()
        
        payload = {
            "decision_id": decision_id,
            "patient_id": patient_id,
            "agent": agent,
            "session_id": session_id,
            "plan": plan or {},
            "verdict": verdict.value if isinstance(verdict, CriticVerdict) else str(verdict) if verdict else None,
            "attempt": attempt,
            "timestamp": now.timestamp(),
            "timestamp_iso": now.isoformat(),
            "reasoning": reasoning,
            "metadata": metadata or {}
        }
        
        # Generate embedding for the decision log
        log_text = f"{agent} agent: {reasoning}"
        embedding_result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=log_text,
            task_type="retrieval_document"
        )
        
        client.upsert(
            collection_name="agent_decisions",
            points=[
                models.PointStruct(
                    id=decision_id,
                    vector=embedding_result["embedding"],
                    payload=payload
                )
            ]
        )
        
        logger.info(f"Logged {agent} decision: {decision_id} (attempt {attempt})")
        return decision_id
        
    except Exception as e:
        logger.error(f"Failed to log agent decision: {e}")
        return ""


def get_agent_trace(
    client: QdrantClient,
    session_id: str,
    limit: int = 50
) -> List[Dict]:
    """
    Retrieves all agent decisions for a session (for UI trace panel).
    As defined in multiagent.md Fix #4.
    
    Args:
        client: Qdrant client instance
        session_id: Session identifier
        limit: Maximum decisions to retrieve
        
    Returns:
        List of decision payloads ordered by timestamp
    """
    try:
        results = client.scroll(
            collection_name="agent_decisions",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="session_id",
                        match=models.MatchValue(value=session_id)
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )[0]
        
        decisions = [point.payload for point in results]
        
        # Sort by timestamp
        decisions.sort(key=lambda x: x.get("timestamp", 0))
        
        return decisions
        
    except Exception as e:
        logger.error(f"Failed to retrieve agent trace: {e}")
        return []


def get_recent_decisions(
    client: QdrantClient,
    patient_id: str,
    agent: Optional[str] = None,
    hours: int = 24,
    limit: int = 100
) -> List[Dict]:
    """
    Retrieves recent agent decisions for a patient.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        agent: Optional agent name filter
        hours: Time window in hours
        limit: Maximum decisions to retrieve
        
    Returns:
        List of recent decision payloads
    """
    try:
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_timestamp = cutoff.timestamp()
        
        filter_conditions = [
            models.FieldCondition(
                key="patient_id",
                match=models.MatchValue(value=patient_id)
            ),
            models.FieldCondition(
                key="timestamp",
                range=models.Range(gte=cutoff_timestamp)
            )
        ]
        
        if agent:
            filter_conditions.append(
                models.FieldCondition(
                    key="agent",
                    match=models.MatchValue(value=agent)
                )
            )
        
        results = client.scroll(
            collection_name="agent_decisions",
            scroll_filter=models.Filter(must=filter_conditions),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )[0]
        
        decisions = [point.payload for point in results]
        decisions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return decisions
        
    except Exception as e:
        logger.error(f"Failed to retrieve recent decisions: {e}")
        return []


def should_trigger(
    verdict: CriticVerdict,
    risk_score: Optional[float] = None,
    threshold: float = 0.5
) -> bool:
    """
    Determines if trigger agent should fire based on verdict and risk score.
    As defined in multiagent.md Fix #7.
    
    Args:
        verdict: Critic verdict
        risk_score: Optional risk score (0-1)
        threshold: Risk threshold
        
    Returns:
        True if trigger should fire
    """
    if verdict in (CriticVerdict.NOT_ENOUGH_EVIDENCE, CriticVerdict.SUGGEST_TRIGGER):
        return True
    
    if risk_score is not None and risk_score > threshold:
        return True
    
    return False


def format_trace_for_ui(decisions: List[Dict]) -> List[Dict]:
    """
    Formats agent decisions for UI display.
    
    Args:
        decisions: List of decision payloads
        
    Returns:
        Formatted list for UI display
    """
    formatted = []
    
    for decision in decisions:
        formatted.append({
            "agent": decision.get("agent", "unknown"),
            "verdict": decision.get("verdict"),
            "attempt": decision.get("attempt", 0),
            "timestamp": decision.get("timestamp_iso", ""),
            "reasoning": decision.get("reasoning", ""),
            "plan_summary": _summarize_plan(decision.get("plan", {}))
        })
    
    return formatted


def _summarize_plan(plan: Dict) -> str:
    """Creates a brief summary of a plan for UI display."""
    if not plan:
        return "No plan"
    
    intent = plan.get("intent", "unknown")
    retrieval = "retrieve" if plan.get("needs_retrieval") else "no retrieval"
    scope = plan.get("temporal_scope", "")
    
    return f"{intent} | {retrieval} | {scope}"


def validate_plan_schema(plan: Dict) -> bool:
    """
    Validates that a plan follows the standard schema.
    
    Args:
        plan: Plan dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "intent",
        "needs_retrieval",
        "temporal_scope",
        "entities",
        "modalities",
        "confidence_threshold",
        "fallback",
        "trigger_if_missing",
        "max_retries"
    ]
    
    for field in required_fields:
        if field not in plan:
            logger.warning(f"Plan missing required field: {field}")
            return False
    
    return True
