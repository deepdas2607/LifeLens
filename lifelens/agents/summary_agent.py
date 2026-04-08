"""
Summary Agent - Family Portal Recap Engine

Generates weekly/monthly memory summaries for family members
with emotional timeline, highlights, and milestone recaps.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
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


def generate_family_summary(
    patient_id: str,
    client: QdrantClient,
    period: str = "week",
    session_id: Optional[str] = None
) -> Dict:
    """
    Generates a narrative summary for family portal.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        patient_id: Patient identifier
        client: QdrantClient instance
        period: "week" or "month"
        session_id: Session ID for logging
        
    Returns:
        {
            "summary": str (narrative summary),
            "emotional_timeline": [list of mood points],
            "highlights": [list of highlight dicts],
            "milestones": [list of milestone dicts],
            "visitor_recap": str,
            "media_gallery": [list of image IDs]
        }
    """
    
    # Determine time range
    days_back = 7 if period == "week" else 30
    now = time.time()
    threshold = now - (days_back * 24 * 3600)
    
    # Gather memories
    memories_data = _get_summary_context(patient_id, client, threshold)
    
    if not groq_client:
        # Basic summary without LLM
        return {
            "summary": f"In the past {period}, {memories_data['total']} memories were captured.",
            "emotional_timeline": [],
            "highlights": [],
            "milestones": memories_data['milestones'],
            "visitor_recap": f"{memories_data['total']} memories recorded.",
            "media_gallery": memories_data['image_ids'][:12]
        }
    
    # Build summary prompt
    memory_descriptions = "\n".join([
        f"- [{m['type']}] {m['content'][:150]}" 
        for m in memories_data['memories'][:20]
    ])
    
    prompt = f"""You are a family recap agent for LifeLens.

**Patient ID:** {patient_id}
**Period:** Past {period} ({days_back} days)

**Memory Summary:**
- Total memories: {memories_data['total']}
- Images: {memories_data['image_count']}
- Audio notes: {memories_data['audio_count']}
- Videos: {memories_data['video_count']}
- Milestones: {len(memories_data['milestones'])}

**Sample Memories:**
{memory_descriptions}

**Emotional Moments:**
{memories_data['sentiment_summary']}

**Your Task:**
Create a warm, engaging family update.

**Include:**
1. **Narrative Summary**: A conversational, heartwarming recap (3-4 paragraphs)
2. **Emotional Timeline**: Key emotional moments with timestamps
3. **Highlights**: Top 5 special moments
4. **Visitor Recap**: Who was present, how often
5. **Media Gallery**: Reference best photo moments

**Tone:**
- Warm and positive
- Family-friendly language
- Celebrate small joys
- Acknowledge challenges gently
- Focus on connection and love

**Output Format:**
{{
    "summary": "Multi-paragraph narrative...",
    "emotional_timeline": [
        {{"date": "2026-02-05", "mood": "joyful", "moment": "Birthday visit from grandchildren"}}
    ],
    "highlights": [
        {{"title": "...", "description": "...", "type": "image|audio|video"}}
    ],
    "visitor_recap": "Text describing visitor patterns",
    "top_memories": ["memory_id1", "memory_id2"]
}}

Respond ONLY with JSON.
"""
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON safely
        summary_data = _safe_json_parse(result_text)
        
        # If empty response, provide friendly defaults
        if not summary_data or 'summary' not in summary_data:
            logger.warning("Empty LLM response, using default summary")
            summary_data = {
                "summary": f"During this {period}, your loved one had {memories_data['total']} special moments captured. Each memory helps preserve precious connections and brings joy to family visits.",
                "emotional_timeline": [{"date": "Recent", "mood": "peaceful", "moment": "Creating lasting memories together"}],
                "highlights": [{"title": "Family Time", "description": "Cherished moments with loved ones", "type": "image"}],
                "visitor_recap": "Family and caregivers continue to create meaningful moments together.",
                "top_memories": memories_data['image_ids'][:5]
            }
        
        # Add media gallery
        summary_data["media_gallery"] = memories_data['image_ids'][:12]
        summary_data["milestones"] = memories_data['milestones']
        
        logger.info(f"Generated {period} summary for {patient_id}")
        
        # Log summary generation decision (multiagent.md Fix #3)
        if session_id:
            try:
                log_agent_decision(
                    client=client,
                    patient_id=patient_id,
                    agent="summary_agent",
                    session_id=session_id,
                    verdict=CriticVerdict.OK,
                    reasoning=f"Generated {period} summary with {len(summary_data.get('highlights', []))} highlights",
                    metadata={
                        "period": period,
                        "total_memories": memories_data['total'],
                        "highlights_count": len(summary_data.get('highlights', [])),
                        "milestones_count": len(memories_data['milestones'])
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log summary decision: {e}")
        
        return summary_data
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return {
            "summary": f"Unable to generate summary: {str(e)}",
            "emotional_timeline": [],
            "highlights": [],
            "milestones": memories_data['milestones'],
            "visitor_recap": "Summary generation error",
            "media_gallery": memories_data['image_ids'][:12]
        }


def _get_summary_context(
    patient_id: str,
    client: QdrantClient,
    timestamp_threshold: float
) -> Dict:
    """
    Gathers memory data for summary generation.
    """
    
    try:
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
        
        all_memories = scroll_result[0]
        
        # Filter by time
        recent_memories = []
        image_count = 0
        audio_count = 0
        video_count = 0
        milestones = []
        image_ids = []
        sentiments = []
        
        for memory in all_memories:
            payload = memory.payload
            timestamp = payload.get("timestamp", 0)
            
            if timestamp >= timestamp_threshold:
                recent_memories.append(memory)
                
                mem_type = payload.get("type", "")
                if mem_type == "image":
                    image_count += 1
                    image_ids.append(memory.id)
                elif mem_type == "audio":
                    audio_count += 1
                elif mem_type == "video":
                    video_count += 1
                
                # Track milestones
                if payload.get("milestone", False):
                    milestones.append({
                        "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
                        "content": payload.get("caption") or payload.get("content", "Milestone")[:100]
                    })
                
                # Track sentiments
                sentiment = payload.get("sentiment", "")
                if sentiment:
                    sentiments.append(sentiment)
        
        # Build memory content list
        memories_for_llm = []
        for memory in recent_memories[:20]:
            payload = memory.payload
            content = ""
            if "caption" in payload:
                content = payload["caption"]
            elif "transcript" in payload:
                content = payload["transcript"]
            elif "analysis" in payload:
                content = payload["analysis"]
            elif "content" in payload:
                content = payload["content"]
            
            memories_for_llm.append({
                "type": payload.get("type", "unknown"),
                "content": content
            })
        
        # Sentiment summary
        sentiment_counts = {}
        for s in sentiments:
            sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
        
        sentiment_summary = ", ".join([f"{k}: {v}" for k, v in sentiment_counts.items()])
        
        return {
            "total": len(recent_memories),
            "image_count": image_count,
            "audio_count": audio_count,
            "video_count": video_count,
            "memories": memories_for_llm,
            "milestones": milestones,
            "image_ids": image_ids,
            "sentiment_summary": sentiment_summary or "No emotional data"
        }
        
    except Exception as e:
        logger.error(f"Error gathering summary context: {e}")
        return {
            "total": 0,
            "image_count": 0,
            "audio_count": 0,
            "video_count": 0,
            "memories": [],
            "milestones": [],
            "image_ids": [],
            "sentiment_summary": "Error"
        }
