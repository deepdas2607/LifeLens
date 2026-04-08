"""
Learning Agent - Longitudinal Pattern Learning

Learns from agent decisions, trigger success, caregiver edits,
and repeated failures to improve system performance over time.

NOTE: This agent has its own legacy logging functions that store in lifelens_memory collection.
The new agent_utils.log_agent_decision stores in agent_decisions collection.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import QDRANT_COLLECTION_NAME
from lifelens.utils.agent_utils import log_agent_decision as log_to_agent_decisions, CriticVerdict
import uuid
import time

logger = logging.getLogger(__name__)


def log_agent_decision(
    client: QdrantClient,
    agent_name: str,
    decision_type: str,
    context: dict,
    outcome: dict,
    patient_id: str = "system"
):
    """
    Stores an agent decision in Qdrant for longitudinal learning.
    
    Args:
        client: QdrantClient instance
        agent_name: Which agent made the decision
        decision_type: Type of decision (e.g., "ingestion_strategy", "trigger", "quality_verdict")
        context: Input context that led to decision
        outcome: Result of the decision
        patient_id: Patient ID (or "system" for global decisions)
    """
    
    try:
        # Create decision record
        decision_payload = {
            "type": "agent_decision",
            "agent_name": agent_name,
            "decision_type": decision_type,
            "context": context,
            "outcome": outcome,
            "timestamp": int(time.time()),
            "patient_id": patient_id
        }
        
        # Store in Qdrant (with zero vector since this is metadata)
        from lifelens.ingestion.upsert_memory import get_embedding
        
        # Create text representation for embedding
        text_repr = f"{agent_name} {decision_type}: {str(context)[:200]} -> {str(outcome)[:200]}"
        vector = get_embedding(text_repr)
        
        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=decision_payload
        )
        
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[point]
        )
        
        logger.info(f"Logged {agent_name} decision: {decision_type}")
        
    except Exception as e:
        logger.error(f"Failed to log agent decision: {e}")


def log_trigger_outcome(
    client: QdrantClient,
    trigger_id: str,
    trigger_type: str,
    sent_at: float,
    caregiver_action: Optional[str],
    patient_id: str
):
    """
    Logs whether a trigger was successful (caregiver responded).
    
    Args:
        client: QdrantClient instance
        trigger_id: ID of the trigger
        trigger_type: Type of trigger
        sent_at: Timestamp when sent
        caregiver_action: What action caregiver took (or None if ignored)
        patient_id: Patient ID
    """
    
    try:
        outcome_payload = {
            "type": "trigger_history",
            "trigger_id": trigger_id,
            "trigger_type": trigger_type,
            "sent_at": sent_at,
            "caregiver_action": caregiver_action,
            "success": caregiver_action is not None,
            "patient_id": patient_id,
            "timestamp": int(time.time())
        }
        
        from lifelens.ingestion.upsert_memory import get_embedding
        text_repr = f"Trigger {trigger_type}: action={caregiver_action}"
        vector = get_embedding(text_repr)
        
        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=outcome_payload
        )
        
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[point]
        )
        
        logger.info(f"Logged trigger outcome: {trigger_type} -> {caregiver_action or 'ignored'}")
        
    except Exception as e:
        logger.error(f"Failed to log trigger outcome: {e}")


def log_caregiver_correction(
    client: QdrantClient,
    memory_id: str,
    original_value: str,
    corrected_value: str,
    field_name: str,
    patient_id: str
):
    """
    Logs when caregiver manually corrects agent output.
    
    Args:
        client: QdrantClient instance
        memory_id: ID of memory that was corrected
        original_value: What agent generated
        corrected_value: What caregiver changed it to
        field_name: Which field was corrected (caption, sentiment, tags, etc.)
        patient_id: Patient ID
    """
    
    try:
        correction_payload = {
            "type": "caregiver_correction",
            "memory_id": memory_id,
            "field_name": field_name,
            "original_value": original_value,
            "corrected_value": corrected_value,
            "patient_id": patient_id,
            "timestamp": int(time.time())
        }
        
        from lifelens.ingestion.upsert_memory import get_embedding
        text_repr = f"Correction {field_name}: {original_value} -> {corrected_value}"
        vector = get_embedding(text_repr)
        
        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=correction_payload
        )
        
        client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[point]
        )
        
        logger.info(f"Logged correction: {field_name} in {memory_id}")
        
    except Exception as e:
        logger.error(f"Failed to log correction: {e}")


def get_learning_insights(
    client: QdrantClient,
    patient_id: str = "system",
    lookback_days: int = 30
) -> Dict:
    """
    Analyzes historical agent decisions and outcomes.
    
    Args:
        client: QdrantClient instance
        patient_id: Patient ID or "system" for global insights
        lookback_days: How far back to analyze
        
    Returns:
        {
            "trigger_success_rate": float,
            "common_corrections": List[Dict],
            "retry_patterns": Dict,
            "recommendations": List[str]
        }
    """
    
    try:
        threshold = time.time() - (lookback_days * 24 * 3600)
        
        # Retrieve learning data
        scroll_result = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        points = scroll_result[0]
        
        # Analyze triggers
        trigger_sent = 0
        trigger_success = 0
        
        # Analyze corrections
        corrections = {}
        
        # Analyze decisions
        decision_types = {}
        
        for point in points:
            payload = point.payload
            timestamp = payload.get("timestamp", 0)
            
            if timestamp < threshold:
                continue
            
            point_type = payload.get("type", "")
            
            if point_type == "trigger_history":
                trigger_sent += 1
                if payload.get("success"):
                    trigger_success += 1
            
            elif point_type == "caregiver_correction":
                field = payload.get("field_name", "unknown")
                corrections[field] = corrections.get(field, 0) + 1
            
            elif point_type == "agent_decision":
                dtype = payload.get("decision_type", "unknown")
                decision_types[dtype] = decision_types.get(dtype, 0) + 1
        
        # Calculate metrics
        trigger_rate = trigger_success / trigger_sent if trigger_sent > 0 else 0
        
        common_corrections = [
            {"field": k, "count": v} 
            for k, v in sorted(corrections.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Generate recommendations
        recommendations = []
        
        if trigger_rate < 0.3:
            recommendations.append("Trigger success rate is low. Consider adjusting trigger logic or timing.")
        
        if corrections.get("caption", 0) > 5:
            recommendations.append("Many caption corrections detected. Consider improving caption quality thresholds.")
        
        if corrections.get("sentiment", 0) > 5:
            recommendations.append("Sentiment corrections detected. Review emotion detection logic.")
        
        return {
            "trigger_success_rate": trigger_rate,
            "trigger_sent": trigger_sent,
            "trigger_success": trigger_success,
            "common_corrections": common_corrections,
            "decision_types": decision_types,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Learning insights failed: {e}")
        return {
            "trigger_success_rate": 0,
            "trigger_sent": 0,
            "trigger_success": 0,
            "common_corrections": [],
            "decision_types": {},
            "recommendations": [],
            "error": str(e)
        }
