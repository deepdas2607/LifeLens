"""
Quality Critic Agent - Validates caption/analysis quality

This agent reviews generated captions and analyses to ensure
they meet LifeLens quality standards for dementia care.
"""

import logging
import json
import re
from typing import Dict, Optional
from groq import Groq
from lifelens.config import GROQ_API_KEY

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


def critique_caption_quality(
    caption: str,
    memory_type: str,
    context: Optional[dict] = None
) -> dict:
    """
    Evaluates caption quality and suggests improvements.
    
    Args:
        caption: Generated caption/analysis text
        memory_type: 'image', 'video', 'audio', 'text'
        context: Optional additional context
        
    Returns:
        {
            "quality_score": 0-10,
            "verdict": "accept" | "retry" | "reject",
            "issues": [list of issues found],
            "suggestions": str,
            "reasoning": str
        }
    """
    
    if not groq_client:
        # Without LLM, accept all captions
        return {
            "quality_score": 7,
            "verdict": "accept",
            "issues": [],
            "suggestions": None,
            "reasoning": "Quality check skipped (no Groq API key)"
        }
    
    prompt = f"""You are a quality critic for LifeLens memory captions.

**Memory Type:** {memory_type}
**Generated Caption:**
{caption}

**Quality Standards for Dementia Care:**
1. **Warmth & Comfort**: Language should be gentle, positive, and reassuring
2. **Clarity**: Descriptions should be specific and easy to understand
3. **People Focus**: When people appear, they should be described warmly
4. **Context**: Include environmental and emotional context
5. **Accessibility**: Suitable for text-to-speech (blind users)
6. **Completeness**: Cover key visual/audio elements
7. **Avoid Generic**: "A person" is worse than "An elderly woman smiling"

**Your Task:**
Evaluate this caption and decide: accept, retry (regenerate), or reject.

**Scoring:**
- 9-10: Excellent - warm, detailed, context-rich
- 7-8: Good - acceptable but could be better
- 5-6: Mediocre - generic or missing key details
- 0-4: Poor - must retry or reject

**Output Format:**
{{
    "quality_score": 0-10,
    "verdict": "accept | retry | reject",
    "issues": ["issue1", "issue2"],
    "suggestions": "How to improve",
    "reasoning": "Why this score"
}}

Respond ONLY with JSON.
"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON
        critique = _safe_json_parse(result_text)
        
        if not critique or 'quality_score' not in critique:
            raise ValueError("Invalid critique response from LLM")
        
        logger.info(f"Caption quality: {critique['quality_score']}/10 - {critique['verdict']}")
        
        return critique
        
    except Exception as e:
        logger.error(f"Quality critique failed: {e}")
        # Default to accepting on error
        return {
            "quality_score": 7,
            "verdict": "accept",
            "issues": [f"Critique error: {str(e)}"],
            "suggestions": None,
            "reasoning": "Error during critique, defaulting to accept"
        }


def should_retry_processing(critique: dict, retry_count: int) -> bool:
    """
    Decides if processing should be retried based on critique.
    
    Args:
        critique: Output from critique_caption_quality
        retry_count: How many retries have occurred
        
    Returns:
        True if should retry, False otherwise
    """
    
    # Never retry more than 2 times
    if retry_count >= 2:
        logger.warning(f"Max retries reached, accepting current result")
        return False
    
    # Retry if verdict is explicit retry
    if critique["verdict"] == "retry":
        return True
    
    # Retry if quality is too low (below 6)
    if critique["quality_score"] < 6:
        return True
    
    return False


def validate_emotion_annotation(
    text_content: str,
    detected_sentiment: str
) -> dict:
    """
    Validates that emotion detection matches content.
    
    Args:
        text_content: Transcript or caption text
        detected_sentiment: Sentiment label (happy, sad, angry, etc.)
        
    Returns:
        {
            "sentiment_valid": bool,
            "corrected_sentiment": str or None,
            "reasoning": str
        }
    """
    
    if not groq_client:
        return {
            "sentiment_valid": True,
            "corrected_sentiment": None,
            "reasoning": "Validation skipped"
        }
    
    prompt = f"""You are validating emotion detection for LifeLens.

**Content:**
{text_content[:500]}

**Detected Sentiment:** {detected_sentiment}

**Your Task:**
Verify if the sentiment label matches the content.

**Output:**
{{
    "sentiment_valid": true/false,
    "corrected_sentiment": "new_label or null",
    "reasoning": "Why"
}}

Respond ONLY with JSON.
"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        result = _safe_json_parse(result_text)
        
        if not result:
            return {"sentiment_valid": True, "corrected_sentiment": None, "reasoning": "Parse error"}
        
        return result
        
    except Exception as e:
        logger.error(f"Sentiment validation failed: {e}")
        return {
            "sentiment_valid": True,
            "corrected_sentiment": None,
            "reasoning": f"Validation error: {e}"
        }
