"""
Analytics Agent - Dashboard Intelligence

Generates insights for the caretaker dashboard by analyzing
memory patterns, trends, and potential concerns.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
import json
import re
from typing import Dict, List, Optional
from groq import Groq
from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import GROQ_API_KEY, QDRANT_COLLECTION_NAME
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict
import time

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


def generate_dashboard_insights(
    patient_id: str,
    client: QdrantClient,
    days_back: int = 7,
    session_id: Optional[str] = None
) -> Dict:
    """
    Generates intelligent insights for the caretaker dashboard.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        patient_id: Patient identifier
        client: QdrantClient instance
        days_back: How many days to analyze
        session_id: Session ID for logging
        
    Returns:
        {
            "insights": [list of insight dicts],
            "warnings": [list of warning dicts],
            "suggestions": [list of suggestion dicts],
            "summary": str
        }
    """
    
    # Gather memory statistics
    stats = _get_analytics_context(patient_id, client, days_back)
    
    if not groq_client:
        # Return basic insights without LLM
        return {
            "insights": [
                {
                    "type": "info",
                    "title": "Memory Activity",
                    "message": f"{stats['total_memories']} memories in last {days_back} days"
                }
            ],
            "warnings": [],
            "suggestions": [],
            "summary": f"Total memories: {stats['total_memories']}"
        }
    
    # Build analysis prompt
    prompt = f"""You are an analytics agent for LifeLens caretaker dashboard.

**Patient Memory Statistics ({days_back} days):**
- Total memories: {stats['total_memories']}
- Images: {stats['image_count']}
- Audio: {stats['audio_count']}
- Videos: {stats['video_count']}
- Text notes: {stats['text_count']}
- Memories per day: {stats['memories_per_day']:.1f}
- Days since last memory: {stats['days_since_last']:.1f}
- Negative sentiment ratio: {stats['negative_ratio']:.1%}
- Milestone captures: {stats['milestone_count']}
- Untagged people: {stats['untagged_count']}

**Your Task:**
Generate actionable insights for the caretaker.

**Categories:**
1. **Insights**: Positive observations or trends
2. **Warnings**: Issues needing attention (gaps, negative trends, missing data)
3. **Suggestions**: Specific actions caretaker should take

**Output Format:**
{{
    "insights": [
        {{"type": "positive", "title": "...", "message": "..."}},
    ],
    "warnings": [
        {{"type": "warning", "title": "...", "message": "...", "action": "..."}}
    ],
    "suggestions": [
        {{"type": "suggestion", "title": "...", "message": "...", "priority": "high|normal"}}
    ],
    "summary": "One-sentence overall assessment"
}}

**Focus on:**
- Memory capture consistency
- Emotional well-being indicators
- Data quality (missing tags, locations)
- Milestone tracking
- Engagement patterns

Respond ONLY with JSON.
"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON safely
        insights_data = _safe_json_parse(result_text)
        
        # If empty response, return friendly defaults
        if not insights_data or 'insights' not in insights_data:
            logger.warning("Empty LLM response, using default insights")
            return {
                "insights": [
                    {"type": "positive", "title": "Memories Preserved", "message": "Your loved one's moments are being safely captured."}
                ],
                "warnings": [],
                "suggestions": [
                    {"type": "suggestion", "title": "Continue Capturing", "message": "Keep uploading photos and videos to build a rich memory collection.", "priority": "normal"}
                ],
                "summary": "Memory collection is active and growing."
            }
        
        logger.info(f"Generated {len(insights_data.get('insights', []))} insights for {patient_id}")
        
        # Log analytics decision (multiagent.md Fix #3)
        if session_id:
            try:
                log_agent_decision(
                    client=client,
                    patient_id=patient_id,
                    agent="analytics",
                    session_id=session_id,
                    verdict=CriticVerdict.OK,
                    reasoning=f"Generated {len(insights_data.get('insights', []))} insights, {len(insights_data.get('warnings', []))} warnings",
                    metadata={
                        "insights_count": len(insights_data.get('insights', [])),
                        "warnings_count": len(insights_data.get('warnings', [])),
                        "suggestions_count": len(insights_data.get('suggestions', [])),
                        "days_analyzed": days_back
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log analytics decision: {e}")
        
        return insights_data
        
    except Exception as e:
        logger.error(f"Analytics agent failed: {e}")
        return {
            "insights": [],
            "warnings": [
                {
                    "type": "error",
                    "title": "Analytics Error",
                    "message": f"Could not generate insights: {str(e)}"
                }
            ],
            "suggestions": [],
            "summary": "Analytics temporarily unavailable"
        }


def _get_analytics_context(
    patient_id: str,
    client: QdrantClient,
    days_back: int
) -> Dict:
    """
    Gathers memory statistics for analytics.
    """
    
    try:
        # Calculate time threshold
        now = time.time()
        threshold = now - (days_back * 24 * 3600)
        
        # Scroll through patient memories
        scroll_result = client.scroll(
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
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        memories = scroll_result[0]
        
        # Analyze memories
        recent_memories = []
        image_count = 0
        audio_count = 0
        video_count = 0
        text_count = 0
        negative_count = 0
        total_sentiment = 0
        milestone_count = 0
        untagged_count = 0
        timestamps = []
        
        for memory in memories:
            payload = memory.payload
            timestamp = payload.get("timestamp", 0)
            
            # Filter by time
            if timestamp >= threshold:
                recent_memories.append(memory)
                timestamps.append(timestamp)
                
                # Count by type
                mem_type = payload.get("type", "")
                if mem_type == "image":
                    image_count += 1
                elif mem_type == "audio":
                    audio_count += 1
                elif mem_type == "video":
                    video_count += 1
                elif mem_type == "text":
                    text_count += 1
                
                # Sentiment analysis
                sentiment = payload.get("sentiment", "").lower()
                if sentiment:
                    total_sentiment += 1
                    if sentiment in ["sad", "angry", "fearful", "negative"]:
                        negative_count += 1
                
                # Milestones
                if payload.get("milestone", False):
                    milestone_count += 1
                
                # Untagged people
                if mem_type in ["image", "video"]:
                    person_tags = payload.get("person_tags", [])
                    if not person_tags or len(person_tags) == 0:
                        untagged_count += 1
        
        total = len(recent_memories)
        days_since_last = (now - max(timestamps)) / 86400 if timestamps else float('inf')
        
        return {
            "total_memories": total,
            "image_count": image_count,
            "audio_count": audio_count,
            "video_count": video_count,
            "text_count": text_count,
            "memories_per_day": total / max(days_back, 1),
            "days_since_last": days_since_last,
            "negative_ratio": negative_count / total_sentiment if total_sentiment > 0 else 0,
            "milestone_count": milestone_count,
            "untagged_count": untagged_count
        }
        
    except Exception as e:
        logger.error(f"Error gathering analytics context: {e}")
        return {
            "total_memories": 0,
            "image_count": 0,
            "audio_count": 0,
            "video_count": 0,
            "text_count": 0,
            "memories_per_day": 0,
            "days_since_last": 0,
            "negative_ratio": 0,
            "milestone_count": 0,
            "untagged_count": 0
        }
