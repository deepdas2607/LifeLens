"""
Executor Agent - Tool Runner

Executes tasks based on Planner decisions:
- Gemini image/video analysis
- Whisper transcription
- Embedding generation
- Qdrant upserts
- Answer generation
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from lifelens.retrieval.reasoning import get_answer
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict

logger = logging.getLogger(__name__)


def execute(plan: dict, retrieved_memories: Optional[List[Dict]], user_query: str,
            patient_id: str, qdrant_client: QdrantClient, session_id: Optional[str] = None) -> str:
    """
    Executes tasks specified in the plan.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        plan: Plan dictionary from Planner agent
        retrieved_memories: Memories from Retriever (can be None or empty)
        user_query: Original user query
        patient_id: Patient identifier  
        qdrant_client: Qdrant client instance
        session_id: Session ID for logging
        
    Returns:
        Generated answer string
    """
    
    logger.info(f"Executor running with plan: {plan.get('reasoning', 'No reasoning provided')}")
    
    # Primary task: Generate answer
    answer = _generate_answer(user_query, retrieved_memories, plan)
    
    # Log execution decision (multiagent.md Fix #3)
    if session_id:
        try:
            log_agent_decision(
                client=qdrant_client,
                patient_id=patient_id,
                agent="executor",
                session_id=session_id,
                verdict=CriticVerdict.OK,
                reasoning=f"Generated answer based on {len(retrieved_memories or [])} memories",
                metadata={
                    "memory_count": len(retrieved_memories or []),
                    "answer_length": len(answer),
                    "plan_reasoning": plan.get("reasoning", "")
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log executor decision: {e}")
    
    # Optional: Run multimodal analysis (future enhancement)
    if plan.get("run_multimodal", False):
        logger.info("Multimodal analysis requested but not yet implemented")
    
    # Optional: Generate recommendations (future enhancement)
    if plan.get("generate_recommendations", False):
        logger.info("Recommendations requested but not yet implemented")
    
    return answer


def _generate_answer(query: str, memories: Optional[List[Dict]], plan: dict) -> str:
    """
    Generates answer using existing reasoning module.
    
    Args:
        query: User query
        memories: Retrieved memories (can be None or empty)
        plan: Plan dictionary
        
    Returns:
        Answer string
    """
    
    # Handle case where no retrieval was performed
    if memories is None:
        memories = []
    
    # If planner decided not to retrieve, provide a direct response
    if not plan.get("retrieve", True) and len(memories) == 0:
        # Check if it's a greeting or general question
        query_lower = query.lower()
        if any(greeting in query_lower for greeting in ["hello", "hi", "hey", "good morning", "good evening"]):
            return "Hello! I'm LifeLens, your memory assistant. I can help you recall your stored memories. What would you like to know?"
        elif any(q in query_lower for q in ["what can you do", "help", "how do you work"]):
            return "I'm LifeLens, your personal memory companion. I can help you:\n\n1. Store memories (photos, audio notes, text)\n2. Recall past events and experiences\n3. Find specific people, places, or moments\n4. Remind you of important things\n\nJust ask me about your memories, and I'll search through what you've stored!"
        else:
            return "I don't have any stored memories to answer that question. Try uploading some memories first, or ask me something else!"
    
    # Use existing get_answer function
    try:
        answer = get_answer(query, memories)
        return answer
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return f"I encountered an error while generating an answer: {str(e)}"
