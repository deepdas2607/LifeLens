"""
Recommender Agent - Memory Capture Suggestions

Suggests what memories to capture next based on gaps and patterns.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from lifelens.utils.ai_prompts import generate_ai_prompts
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict

logger = logging.getLogger(__name__)


def suggest_captures(patient_id: str, qdrant_client: QdrantClient, 
                     session_id: Optional[str] = None) -> List[Dict]:
    """
    Suggests memory capture prompts based on patient patterns.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        patient_id: Patient identifier
        qdrant_client: Qdrant client instance
        session_id: Session ID for logging
        
    Returns:
        List of suggestion dictionaries
    """
    
    try:
        from lifelens.config import QDRANT_COLLECTION_NAME
        from qdrant_client.http import models
        
        # Get recent memories (excluding agent decisions)
        recent_results = qdrant_client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=20,
            with_payload=True,
            with_vectors=False,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ],
                must_not=[
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="agent_decision")
                    )
                ]
            )
        )[0]
        
        recent_memories = [p.payload for p in recent_results]
        last_upload = max([m.get("timestamp", 0) for m in recent_memories]) if recent_memories else None
        
        # Use existing AI prompts logic
        suggestions = generate_ai_prompts(recent_memories, last_upload)
        
        logger.info(f"Generated {len(suggestions)} capture suggestions")
        
        # Log recommendation decision (multiagent.md Fix #3)
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="recommender",
                    session_id=session_id,
                    verdict=CriticVerdict.OK,
                    reasoning=f"Generated {len(suggestions)} capture suggestions based on {len(recent_memories)} recent memories",
                    metadata={
                        "suggestion_count": len(suggestions),
                        "recent_memory_count": len(recent_memories),
                        "last_upload": last_upload
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log recommender decision: {e}")
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Capture suggestion generation failed: {e}")
        
        # Log failure
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="recommender",
                    session_id=session_id,
                    verdict=CriticVerdict.IGNORE,
                    reasoning=f"Suggestion generation failed: {str(e)}",
                    metadata={"error": str(e)}
                )
            except Exception as log_error:
                logger.warning(f"Failed to log recommender error: {log_error}")
        
        return []


def identify_gaps(patient_stats: Dict) -> List[str]:
    """
    Identifies missing memory types or patterns.
    
    Args:
        patient_stats: Patient statistics dictionary
        
    Returns:
        List of gap descriptions
    """
    
    gaps = []
    
    # Check for missing memory types
    types = patient_stats.get("types_count", {})
    if types.get("image", 0) == 0:
        gaps.append("No photos uploaded yet")
    if types.get("audio", 0) == 0:
        gaps.append("No audio notes recorded")
    if types.get("text", 0) == 0:
        gaps.append("No text notes written")
    
    # Check for recent activity
    if patient_stats.get("recent_count", 0) == 0:
        gaps.append("No recent memories (last 7 days)")
    
    return gaps
