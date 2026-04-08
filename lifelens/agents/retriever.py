"""
Retriever Agent - Qdrant Specialist

Executes retrieval only when Planner requests it.
Performs semantic search with plan-specified filters.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from lifelens.retrieval.search_engine import search_memories
from lifelens.retrieval.time_parser import parse_time_filter
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict

logger = logging.getLogger(__name__)


def search(query: str, patient_id: str, plan: dict, qdrant_client: QdrantClient, 
           session_id: Optional[str] = None) -> List[Dict]:
    """
    Performs semantic search based on Planner's strategy.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        query: User query string
        patient_id: Patient identifier
        plan: Plan dictionary from Planner agent
        qdrant_client: Qdrant client instance
        session_id: Session ID for logging
        
    Returns:
        List of ranked memories with scores
    """
    
    if not plan.get("retrieve", True):
        logger.info("Planner decided not to retrieve. Returning empty results.")
        
        # Log skip decision
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="retriever",
                    session_id=session_id,
                    verdict=CriticVerdict.IGNORE,
                    reasoning="Planner set needs_retrieval=False, skipping search",
                    metadata={"skipped": True}
                )
            except Exception as e:
                logger.warning(f"Failed to log retriever decision: {e}")
        
        return []
    
    # Parse filters from plan
    filters = _parse_filters(plan.get("filters", []), query)
    
    logger.info(f"Retriever executing search with filters: {filters}")
    
    try:
        # Use existing search_memories function
        results = search_memories(
            client=qdrant_client,
            query=query,
            filters=filters,
            top_k=10,
            patient_id=patient_id
        )
        
        logger.info(f"Retriever found {len(results)} memories")
        
        # Log retrieval decision (multiagent.md Fix #3)
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="retriever",
                    session_id=session_id,
                    verdict=CriticVerdict.OK,
                    reasoning=f"Retrieved {len(results)} memories with filters: {filters}",
                    metadata={
                        "result_count": len(results),
                        "filters": filters,
                        "top_scores": [r.get("score", 0.0) for r in results[:3]] if results else []
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log retriever decision: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Retriever search failed: {e}")
        
        # Log failure
        if session_id:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="retriever",
                    session_id=session_id,
                    verdict=CriticVerdict.IGNORE,
                    reasoning=f"Search failed: {str(e)}",
                    metadata={"error": str(e)}
                )
            except Exception as log_error:
                logger.warning(f"Failed to log retriever error: {log_error}")
        
        return []


def _parse_filters(filter_list: List[str], query: str) -> Optional[Dict]:
    """
    Converts plan filters to Qdrant filter format.
    
    Args:
        filter_list: List of filter strings from plan (e.g., ["time:last_week", "type:image"])
        query: Original query for time parsing
        
    Returns:
        Dictionary of filters compatible with search_memories
    """
    
    filters = {}
    
    for filter_str in filter_list:
        if ":" not in filter_str:
            continue
            
        filter_type, filter_value = filter_str.split(":", 1)
        
        if filter_type == "time":
            # Use existing time parser
            time_filters = parse_time_filter(query)
            if time_filters:
                filters.update(time_filters)
                
        elif filter_type == "type":
            # Memory type filter
            if "type" not in filters:
                filters["type"] = []
            filters["type"].append(filter_value)
            
        elif filter_type == "mood":
            # Mood/sentiment filter
            if "mood" not in filters:
                filters["mood"] = []
            filters["mood"].append(filter_value)
    
    return filters if filters else None
