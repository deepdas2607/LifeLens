"""
Planner Agent - Strategy Generator

LLM-powered agent that decides:
- Whether to retrieve memories
- Which modalities to inspect
- Whether triggers should fire
- Whether recommendations are needed
- Whether to retry search
"""

import logging
import json
import re
import uuid
from typing import Dict, List, Optional
from groq import Groq
from qdrant_client import QdrantClient
from lifelens.config import GROQ_API_KEY, QDRANT_COLLECTION_NAME
from lifelens.utils.agent_utils import (
    create_standard_plan,
    log_agent_decision,
    Intent,
    CriticVerdict
)

logger = logging.getLogger(__name__)


def _safe_json_parse(text: str) -> dict:
    """Safely parse JSON from LLM response, handling code blocks and errors."""
    if not text:
        return {}
    
    # Remove markdown code blocks if present
    text = text.strip()
    if '```' in text:
        # Extract content between ```json and ``` or ``` and ```
        match = re.search(r'```(?:json)?\s*\n?({[^`]+})\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # Try to find any JSON object
            match = re.search(r'{[^{}]*(?:{[^{}]*}[^{}]*)*}', text, re.DOTALL)
            if match:
                text = match.group(0)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}. Text: {text[:200]}")
        return {}


def plan(user_query: str, patient_id: str, qdrant_client: QdrantClient, session_id: Optional[str] = None) -> dict:
    """
    Analyzes user query and generates a standardized retrieval/execution plan.
    Follows multiagent.md Fix #1 - Unified Planner Schema.
    
    Args:
        user_query: The user's question or request
        patient_id: Patient identifier
        qdrant_client: Qdrant client for pattern analysis
        session_id: Optional session ID for tracking
        
    Returns:
        Standard plan dictionary following multiagent.md schema
    """
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Get basic patient stats for context
    try:
        stats = _get_patient_context(patient_id, qdrant_client)
    except Exception as e:
        logger.warning(f"Could not fetch patient context: {e}")
        stats = {"total_memories": 0, "recent_count": 0}
    
    # Build planning prompt
    system_prompt = f"""You are the Planner Agent for LifeLens, a memory assistant system.

Your job is to analyze the user's query and decide the best strategy to answer it.

PATIENT CONTEXT:
- Total memories stored: {stats.get('total_memories', 0)}
- Recent memories (last 7 days): {stats.get('recent_count', 0)}
- Memory types available: {stats.get('types', [])}

USER QUERY: "{user_query}"

DECISION RULES:
1. If the query asks about past events, people, or memories → set retrieve=true
2. If the query is a greeting or general question → set retrieve=false
3. If asking about recent events → add time filter
4. If asking about specific people → add person filter
5. If asking about photos/images → add type filter
6. If the query seems to need more data → set trigger_followup=true

OUTPUT FORMAT (JSON only, no other text):
{{
  "retrieve": true/false,
  "filters": ["time:last_week", "type:image"],
  "run_multimodal": false,
  "generate_recommendations": false,
  "trigger_followup": false,
  "reasoning": "brief explanation of your decision"
}}

Respond with ONLY the JSON object, nothing else."""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a planning agent that outputs only JSON."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.2,
            max_tokens=512,
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Parse JSON response safely
        plan_dict = _safe_json_parse(response_text)
        
        if not plan_dict or 'retrieve' not in plan_dict:
            raise ValueError("Invalid plan response from LLM")
        
        logger.info(f"Planner generated plan: {plan_dict}")
        
        # Transform to standard schema (multiagent.md Fix #1)
        entities = [word for word in user_query.split() if word and len(word) > 1 and word[0].isupper()]
        
        standard_plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            needs_retrieval=plan_dict.get("retrieve", True),
            temporal_scope=_extract_temporal_scope(plan_dict.get("filters", [])),
            entities=entities[:5],  # Limit to 5 entities
            modalities=_extract_modalities(plan_dict.get("filters", [])),
            confidence_threshold=0.75,
            fallback="ask_caretaker",
            trigger_if_missing=plan_dict.get("trigger_followup", False),
            max_retries=2,
            # Legacy fields for backward compatibility
            retrieve=plan_dict.get("retrieve", True),
            filters=plan_dict.get("filters", []),
            run_multimodal=plan_dict.get("run_multimodal", False),
            generate_recommendations=plan_dict.get("generate_recommendations", False),
            trigger_followup=plan_dict.get("trigger_followup", False),
            reasoning=plan_dict.get("reasoning", "")
        )
        
        # Log plan to Qdrant
        try:
            log_agent_decision(
                client=qdrant_client,
                patient_id=patient_id,
                agent="planner",
                session_id=session_id,
                plan=standard_plan,
                attempt=0,
                reasoning=plan_dict.get("reasoning", "Initial plan generated")
            )
        except Exception as log_error:
            logger.warning(f"Failed to log plan decision: {log_error}")
        
        return standard_plan
        
    except Exception as e:
        logger.error(f"Planner failed: {e}")
        # Fallback plan with standard schema
        fallback_plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            needs_retrieval=True,
            temporal_scope="last_week",
            entities=[],
            modalities=["text", "image", "audio", "video"],
            confidence_threshold=0.75,
            fallback="ask_caretaker",
            trigger_if_missing=False,
            max_retries=2,
            # Legacy fields
            retrieve=True,
            filters=[],
            run_multimodal=False,
            generate_recommendations=False,
            trigger_followup=False,
            reasoning=f"Fallback plan due to error: {str(e)}"
        )
        
        # Log fallback
        try:
            log_agent_decision(
                client=qdrant_client,
                patient_id=patient_id,
                agent="planner",
                session_id=session_id,
                plan=fallback_plan,
                attempt=0,
                reasoning=f"Fallback plan: {str(e)}"
            )
        except:
            pass
        
        return fallback_plan


def replan(user_query: str, patient_id: str, previous_result: str, 
           critic_feedback: str, qdrant_client: QdrantClient, 
           session_id: Optional[str] = None) -> dict:
    """
    Adjusts plan based on Critic feedback.
    Implements multiagent.md Fix #2 - Replanning loop.
    
    Args:
        user_query: Original user query
        patient_id: Patient identifier
        previous_result: Previous answer that failed
        critic_feedback: Feedback from Critic agent
        qdrant_client: Qdrant client
        session_id: Session ID for tracking
        
    Returns:
        Updated standard plan dictionary
    """
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    system_prompt = f"""You are the Planner Agent for LifeLens. Your previous plan didn't work well.

USER QUERY: "{user_query}"

PREVIOUS RESULT: "{previous_result}"

CRITIC FEEDBACK: "{critic_feedback}"

Based on this feedback, create a NEW plan to better answer the query.

ADJUSTMENTS TO CONSIDER:
- If "no relevant memories" → try broader filters or different time range
- If "hallucination detected" → be more strict with retrieval
- If "missing context" → set trigger_followup=true to request more data
- If "low confidence" → try different search terms or filters

OUTPUT FORMAT (JSON only):
{{
  "retrieve": true/false,
  "filters": ["adjusted filters"],
  "run_multimodal": false,
  "generate_recommendations": false,
  "trigger_followup": false,
  "reasoning": "explanation of adjustments"
}}

Respond with ONLY the JSON object."""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a planning agent that outputs only JSON."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.3,
            max_tokens=512,
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Parse JSON safely
        plan_dict = _safe_json_parse(response_text)
        
        if not plan_dict or 'retrieve' not in plan_dict:
            raise ValueError("Invalid replan response from LLM")
        
        logger.info(f"Planner re-generated plan: {plan_dict}")
        
        # Transform to standard schema
        entities = [word for word in user_query.split() if word and len(word) > 1 and word[0].isupper()]
        
        standard_plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            needs_retrieval=plan_dict.get("retrieve", True),
            temporal_scope=_extract_temporal_scope(plan_dict.get("filters", [])),
            entities=entities[:5],
            modalities=_extract_modalities(plan_dict.get("filters", [])),
            confidence_threshold=0.75,
            fallback="ask_caretaker",
            trigger_if_missing=plan_dict.get("trigger_followup", True),
            max_retries=1,  # Reduce retries on replan
            # Legacy fields
            retrieve=plan_dict.get("retrieve", True),
            filters=plan_dict.get("filters", []),
            run_multimodal=plan_dict.get("run_multimodal", False),
            generate_recommendations=plan_dict.get("generate_recommendations", False),
            trigger_followup=plan_dict.get("trigger_followup", True),
            reasoning=plan_dict.get("reasoning", "")
        )
        
        # Log replan to Qdrant
        try:
            log_agent_decision(
                client=qdrant_client,
                patient_id=patient_id,
                agent="planner",
                session_id=session_id,
                plan=standard_plan,
                attempt=1,  # Replan is always attempt 1+
                reasoning=f"Replan: {plan_dict.get('reasoning', 'Adjusted based on feedback')}"
            )
        except Exception as log_error:
            logger.warning(f"Failed to log replan decision: {log_error}")
        
        return standard_plan
        
    except Exception as e:
        logger.error(f"Replanner failed: {e}")
        # Fallback with standard schema
        fallback_plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            needs_retrieval=True,
            temporal_scope="last_month",  # Broader scope
            entities=[],
            modalities=["text", "image", "audio", "video"],
            confidence_threshold=0.75,
            fallback="ask_caretaker",
            trigger_if_missing=True,
            max_retries=1,
            # Legacy fields
            retrieve=True,
            filters=[],
            run_multimodal=False,
            generate_recommendations=False,
            trigger_followup=True,
            reasoning=f"Fallback replan due to error: {str(e)}"
        )
        
        try:
            log_agent_decision(
                client=qdrant_client,
                patient_id=patient_id,
                agent="planner",
                session_id=session_id,
                plan=fallback_plan,
                attempt=1,
                reasoning=f"Fallback replan: {str(e)}"
            )
        except:
            pass
        
        return fallback_plan


def _get_patient_context(patient_id: str, qdrant_client: QdrantClient) -> dict:
    """
    Fetches basic patient statistics for planning context.
    
    Args:
        patient_id: Patient identifier
        qdrant_client: Qdrant client
        
    Returns:
        Dictionary with patient stats
    """
    import time
    from qdrant_client.http import models
    
    try:
        # Get total count (excluding agent decisions)
        total_result = qdrant_client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
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
            ),
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        all_memories = total_result[0]
        total_count = len(all_memories)
        
        # Count recent (last 7 days)
        week_ago = int(time.time()) - (7 * 24 * 60 * 60)
        recent_count = sum(1 for m in all_memories if m.payload.get("timestamp", 0) > week_ago)
        
        # Get memory types
        types = list(set(m.payload.get("type") for m in all_memories if m.payload.get("type") and m.payload.get("type") != "agent_decision"))
        
        return {
            "total_memories": total_count,
            "recent_count": recent_count,
            "types": types
        }
        
    except Exception as e:
        logger.error(f"Failed to get patient context: {e}")
        return {"total_memories": 0, "recent_count": 0, "types": []}


def _extract_temporal_scope(filters: List[str]) -> str:
    """
    Extracts temporal scope from filter strings.
    
    Args:
        filters: List of filter strings
        
    Returns:
        Temporal scope string
    """
    for f in filters:
        if "last_week" in f.lower():
            return "last_week"
        if "last_month" in f.lower():
            return "last_month"
        if "recent" in f.lower():
            return "last_week"
        if "last_year" in f.lower():
            return "last_year"
    return "last_week"  # Default


def _extract_modalities(filters: List[str]) -> List[str]:
    """
    Extracts modalities from filter strings.
    
    Args:
        filters: List of filter strings
        
    Returns:
        List of modality strings
    """
    modalities = []
    for f in filters:
        f_lower = f.lower()
        if "image" in f_lower or "photo" in f_lower or "picture" in f_lower:
            modalities.append("image")
        if "video" in f_lower:
            modalities.append("video")
        if "audio" in f_lower or "voice" in f_lower:
            modalities.append("audio")
        if "text" in f_lower:
            modalities.append("text")
    
    # If no specific modalities found, return all
    if not modalities:
        return ["text", "image", "audio", "video"]
    
    return list(set(modalities))  # Remove duplicates
