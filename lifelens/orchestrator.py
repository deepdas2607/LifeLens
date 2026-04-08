"""
Orchestrator - Multi-Agent Coordination

Coordinates agent interactions in an autonomous loop:
1. Planner decides strategy
2. Retriever searches (if requested)
3. Executor generates answer
4. Critic evaluates
5. Retry if needed
6. Trigger agent generates proactive alerts

Compliant with multiagent.md Fix #2 - Retry & Replanning Loop
"""

import logging
import uuid
from typing import Dict, List, Optional
from qdrant_client import QdrantClient
from lifelens.agents import planner, retriever, executor, critic, trigger, recommender
from lifelens.utils.agent_utils import CriticVerdict, log_agent_decision, should_trigger

logger = logging.getLogger(__name__)


def run_agentic_flow(user_query: str, patient_id: str, qdrant_client: QdrantClient, 
                     max_retries: int = 2) -> Dict:
    """
    Main orchestration loop for multi-agent system.
    Implements multiagent.md Fix #2 - Retry & Replanning Loop.
    
    Args:
        user_query: User's question or request
        patient_id: Patient identifier
        qdrant_client: Qdrant client instance
        max_retries: Maximum number of retry attempts (default: 2)
        
    Returns:
        Dictionary containing:
        - answer: Generated answer string
        - sources: Retrieved memories (can be empty)
        - triggers: List of generated triggers
        - plan: Planner's strategy
        - verdict: Critic's evaluation (CriticVerdict enum value)
        - retry_count: Number of retries performed
        - session_id: Unique session identifier for tracing
    """
    
    # Generate session ID for tracking this entire flow
    session_id = str(uuid.uuid4())
    logger.info(f"Starting agentic flow [session: {session_id}] for query: '{user_query}'")
    
    # Step 1: Planner decides strategy
    plan = planner.plan(user_query, patient_id, qdrant_client, session_id=session_id)
    logger.info(f"Plan: {plan.get('reasoning', 'No reasoning')}")
    
    # Initialize loop variables
    attempt = 0
    verdict = None
    retrieved = []
    result = ""
    max_attempts = plan.get("max_retries", max_retries)
    
    #Retry/replanning loop (multiagent.md Fix #2)
    while attempt <= max_attempts:
        logger.info(f"Attempt {attempt + 1}/{max_attempts + 1}")
        
        # Step 2: Conditional retrieval (multiagent.md Fix #5)
        if plan.get("needs_retrieval", True) or plan.get("retrieve", True):
            retrieved = retriever.search(user_query, patient_id, plan, qdrant_client, session_id=session_id)
            logger.info(f"Retrieved {len(retrieved)} memories")
        else:
            logger.info("Plan decided: no retrieval needed")
            retrieved = []
        
        # Step 3: Executor generates answer
        result = executor.execute(plan, retrieved, user_query, patient_id, qdrant_client, session_id=session_id)
        logger.info(f"Executor generated answer: {result[:100]}...")
        
        # Step 4: Critic evaluates
        verdict = critic.evaluate(user_query, result, retrieved, session_id, patient_id, qdrant_client)
        logger.info(f"Critic verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict}")
        
        # Convert string verdict to enum if needed (backward compatibility)
        if isinstance(verdict, str):
            verdict_mapping = {
                "OK": CriticVerdict.OK,
                "RETRY_RETRIEVAL": CriticVerdict.RETRY,
                "SUGGEST_TRIGGER": CriticVerdict.SUGGEST_TRIGGER,
                "REQUEST_MORE_DATA": CriticVerdict.NOT_ENOUGH_EVIDENCE
            }
            verdict = verdict_mapping.get(verdict, CriticVerdict.OK)
        
        # Check if done
        if verdict == CriticVerdict.OK:
            logger.info("Critic approved answer - flow complete")
            break
        
        # Step 5: Replan if retry needed
        if verdict == CriticVerdict.RETRY and attempt < max_attempts:
            logger.info(f"Critic requested RETRY - replanning (attempt {attempt + 1}/{max_attempts})...")
            
            plan = planner.replan(user_query, patient_id, result, verdict.value, qdrant_client)
            attempt += 1
        else:
            logger.info("Max retries reached or verdict doesn't require retry")
            break
    
            logger.info("Max retries reached or verdict doesn't require retry")
            break
    
    # Step 6: Conditional trigger generation (multiagent.md Fix #7)
    triggers = []
    if should_trigger(verdict):
        logger.info("Trigger conditions met - generating proactive alerts")
        triggers = trigger.generate(verdict, patient_id, qdrant_client, session_id=session_id)
        logger.info(f"Generated {len(triggers)} triggers")
    else:
        logger.info(f"Trigger conditions not met for verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict}")
    
    # Step 7: Generate recommendations (if needed)
    recommendations = []
    if plan.get("generate_recommendations", False) or plan.get("trigger_if_missing", False) or \
       verdict in (CriticVerdict.NOT_ENOUGH_EVIDENCE, CriticVerdict.SUGGEST_TRIGGER):
        try:
            recommendations = recommender.suggest_captures(patient_id, qdrant_client, session_id=session_id)
            logger.info(f"Generated {len(recommendations)} capture recommendations")
        except Exception as e:
            logger.warning(f"Failed to generate recommendations: {e}")
    
    # Log final orchestrator decision
    try:
        log_agent_decision(
            client=qdrant_client,
            patient_id=patient_id,
            agent="orchestrator",
            session_id=session_id,
            verdict=verdict,
            attempt=attempt,
            reasoning=f"Flow completed after {attempt + 1} attempts with verdict: {verdict.value if isinstance(verdict, CriticVerdict) else verdict}",
            metadata={
                "query": user_query,
                "total_attempts": attempt + 1,
                "sources_count": len(retrieved),
                "triggers_count": len(triggers),
                "recommendations_count": len(recommendations)
            }
        )
    except Exception as e:
        logger.warning(f"Failed to log orchestrator decision: {e}")
    
    return {
        "answer": result,
        "sources": retrieved if retrieved else [],
        "triggers": triggers,
        "recommendations": recommendations,
        "plan": plan,
        "verdict": verdict.value if isinstance(verdict, CriticVerdict) else verdict,
        "retry_count": attempt,
        "session_id": session_id  # Include for UI tracing
    }


def _log_decision(qdrant_client: QdrantClient, patient_id: str, query: str, 
                  plan: Dict, verdict: str, answer: str):
    """
    Logs agent decision to Qdrant for learning and analytics using Learning Agent.
    
    Args:
        qdrant_client: Qdrant client instance
        patient_id: Patient identifier
        query: User query
        plan: Planner's decision
        verdict: Critic's verdict
        answer: Generated answer
    """
    
    try:
        from lifelens.agents import log_agent_decision
        
        # Use learning agent to log decision
        log_agent_decision(
            client=qdrant_client,
            agent_name="orchestrator",
            decision_type="query_flow",
            context={
                "query": query,
                "plan_reasoning": plan.get("reasoning", ""),
                "retrieve": plan.get("retrieve", True),
                "keywords": plan.get("keywords", [])
            },
            outcome={
                "verdict": verdict,
                "answer_preview": answer[:200],
                "answer_length": len(answer)
            },
            patient_id=patient_id
        )
        
        logger.info("Logged agent decision via Learning Agent")
        
    except Exception as e:
        logger.error(f"Failed to log decision: {e}")
        # Don't raise - logging is optional
