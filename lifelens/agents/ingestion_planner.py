"""
Ingestion Planner Agent - Decides memory processing strategy

This agent analyzes uploaded content and creates an intelligent
processing plan before ingestion begins.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
import os
import json
import re
from typing import Optional
from groq import Groq
from qdrant_client import QdrantClient
from lifelens.config import GROQ_API_KEY
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


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


def plan_ingestion_strategy(
    file_type: str,
    file_name: str,
    file_size: int,
    patient_id: str,
    qdrant_client: Optional[QdrantClient] = None,
    patient_context: Optional[dict] = None,
    session_id: Optional[str] = None
) -> dict:
    """
    Creates an intelligent ingestion plan based on file characteristics.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        file_type: Type of file (image, audio, video, text)
        file_name: Name of uploaded file
        file_size: Size in bytes
        patient_id: Patient identifier
        qdrant_client: Qdrant client for logging
        patient_context: Optional patient history context
        session_id: Session ID for logging
        
    Returns:
        Dictionary with processing strategy:
        {
            "strategy": "full_analysis" | "quick_analysis" | "skip",
            "use_video_frames": bool,
            "caption_depth": "detailed" | "basic",
            "extract_people": bool,
            "extract_location": bool,
            "priority": "high" | "normal" | "low",
            "reasoning": str
        }
    """
    
    if not groq_client:
        # Fallback to basic strategy without LLM
        return {
            "strategy": "full_analysis",
            "use_video_frames": file_type == "video",
            "caption_depth": "detailed",
            "extract_people": True,
            "extract_location": True,
            "priority": "normal",
            "reasoning": "Default strategy (no Groq API key)"
        }
    
    # Build prompt
    prompt = f"""You are an ingestion planning agent for LifeLens, a memory assistant for dementia patients.

**Uploaded File:**
- Type: {file_type}
- Name: {file_name}
- Size: {file_size / 1024:.1f} KB

**Patient Context:**
{patient_context if patient_context else "No recent activity data available"}

**Your Task:**
Decide the best processing strategy for this memory.

**Consider:**
1. File type and size (large videos need selective frame analysis)
2. File name hints (birthday, medication, milestone keywords)
3. Patient activity patterns (gaps suggest higher priority)
4. Processing cost vs. value

**Output Format (JSON-like):**
{{
    "strategy": "full_analysis | quick_analysis | skip",
    "use_video_frames": true/false,
    "caption_depth": "detailed | basic",
    "extract_people": true/false,
    "extract_location": true/false,
    "priority": "high | normal | low",
    "reasoning": "Brief explanation of decision"
}}

Respond ONLY with the JSON object, no other text.
"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        plan_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        plan = _safe_json_parse(plan_text)
        
        if not plan or 'strategy' not in plan:
            raise ValueError("Invalid plan response from LLM")
        
        logger.info(f"Ingestion plan created: {plan['strategy']} for {file_name}")
        
        # Log ingestion plan decision (multiagent.md Fix #3)
        if session_id and qdrant_client:
            try:
                log_agent_decision(
                    client=qdrant_client,
                    patient_id=patient_id,
                    agent="ingestion_planner",
                    session_id=session_id,
                    verdict=CriticVerdict.OK,
                    reasoning=f"Created {plan['strategy']} plan for {file_type} file",
                    metadata={
                        "file_type": file_type,
                        "file_name": file_name,
                        "file_size": file_size,
                        "strategy": plan['strategy'],
                        "priority": plan.get('priority', 'normal')
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log ingestion plan decision: {e}")
        
        return plan
        
    except Exception as e:
        logger.error(f"Ingestion planning failed: {e}")
        # Fallback strategy
        return {
            "strategy": "full_analysis",
            "use_video_frames": file_type == "video",
            "caption_depth": "detailed",
            "extract_people": True,
            "extract_location": True,
            "priority": "normal",
            "reasoning": f"Error in planning, using safe defaults: {str(e)}"
        }


def should_trigger_follow_up(
    processed_result: dict,
    strategy: dict
) -> dict:
    """
    After processing, decides if caregiver follow-up is needed.
    
    Args:
        processed_result: Output from image/video/audio processor
        strategy: Original ingestion plan
        
    Returns:
        {
            "trigger_needed": bool,
            "trigger_type": "review" | "add_tags" | "clarify" | None,
            "message": str
        }
    """
    
    if not groq_client:
        return {"trigger_needed": False, "trigger_type": None, "message": None}
    
    # Build analysis prompt
    content_preview = ""
    if "caption" in processed_result:
        content_preview = processed_result["caption"][:300]
    elif "analysis" in processed_result:
        content_preview = processed_result["analysis"][:300]
    elif "transcript" in processed_result:
        content_preview = processed_result["transcript"][:300]
    
    prompt = f"""You are a follow-up trigger agent for LifeLens memory ingestion.

**Processed Memory Content:**
{content_preview}

**Original Plan Priority:** {strategy.get('priority', 'normal')}

**Your Task:**
Decide if caregiver follow-up is needed.

**Trigger Criteria:**
- Missing people identification ("a person", "someone")
- Negative sentiment (sadness, fear, anger)
- Medication mentions without context
- Milestone moments (birthday, anniversary)
- Low quality captions (very generic descriptions)

**Output Format:**
{{
    "trigger_needed": true/false,
    "trigger_type": "review | add_tags | clarify | None",
    "message": "Brief message for caregiver"
}}

Respond ONLY with JSON.
"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        result = _safe_json_parse(result_text)
        
        if not result:
            return {"trigger_needed": False, "trigger_type": None, "message": None}
        
        return result
        
    except Exception as e:
        logger.error(f"Follow-up trigger check failed: {e}")
        return {"trigger_needed": False, "trigger_type": None, "message": None}
