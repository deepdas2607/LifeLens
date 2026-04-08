"""
Hygiene Agent - Memory Maintenance & Data Quality

Identifies duplicates, low-quality memories, missing metadata,
and suggests cleanup actions for caretaker approval.
Implements multiagent.md Fix #3 - Qdrant logging.
"""

import logging
from typing import Dict, List, Tuple, Optional
from groq import Groq
from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import GROQ_API_KEY, QDRANT_COLLECTION_NAME
from lifelens.utils.agent_utils import log_agent_decision, CriticVerdict
import time

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def scan_for_hygiene_issues(
    patient_id: str,
    client: QdrantClient,
    session_id: Optional[str] = None
) -> Dict:
    """
    Scans patient memories for data quality issues.
    Implements multiagent.md Fix #3 - Decision logging.
    
    Args:
        patient_id: Patient identifier
        client: QdrantClient instance
        session_id: Session ID for logging
        
    Returns:
        {
            "duplicates": [list of potential duplicate pairs],
            "low_quality": [list of memories with quality issues],
            "missing_metadata": [list of memories with missing tags/locations],
            "orphaned_media": [list of memories with broken references],
            "recommendations": [list of cleanup actions]
        }
    """
    
    try:
        # Retrieve all patient memories
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
            limit=2000,
            with_payload=True,
            with_vectors=True
        )
        
        memories = scroll_result[0]
        
        # Run analysis
        duplicates = _find_duplicates(memories, client)
        low_quality = _find_low_quality(memories)
        missing_metadata = _find_missing_metadata(memories)
        orphaned = _find_orphaned_media(memories)
        
        # Generate recommendations
        recommendations = _generate_cleanup_recommendations(
            duplicates, low_quality, missing_metadata, orphaned
        )
        
        logger.info(f"Hygiene scan complete: {len(duplicates)} duplicates, {len(low_quality)} low quality")
        
        # Log hygiene scan decision (multiagent.md Fix #3)
        if session_id:
            try:
                log_agent_decision(
                    client=client,
                    patient_id=patient_id,
                    agent="hygiene",
                    session_id=session_id,
                    verdict=CriticVerdict.OK,
                    reasoning=f"Scanned {len(memories)} memories, found {len(duplicates)} duplicates, {len(low_quality)} low quality",
                    metadata={
                        "duplicates_count": len(duplicates),
                        "low_quality_count": len(low_quality),
                        "missing_metadata_count": len(missing_metadata),
                        "orphaned_count": len(orphaned),
                        "total_scanned": len(memories)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log hygiene decision: {e}")
        
        return {
            "duplicates": duplicates,
            "low_quality": low_quality,
            "missing_metadata": missing_metadata,
            "orphaned_media": orphaned,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Hygiene scan failed: {e}")
        return {
            "duplicates": [],
            "low_quality": [],
            "missing_metadata": [],
            "orphaned_media": [],
            "recommendations": [],
            "error": str(e)
        }


def _find_duplicates(memories: List, client: QdrantClient) -> List[Dict]:
    """
    Finds potential duplicate memories using vector similarity.
    """
    
    duplicates = []
    processed_ids = set()
    
    for memory in memories:
        if memory.id in processed_ids:
            continue
        
        # Search for similar vectors
        try:
            search_result = client.query_points(
                collection_name=QDRANT_COLLECTION_NAME,
                query=memory.vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="patient_id",
                            match=models.MatchValue(value=memory.payload.get("patient_id"))
                        )
                    ]
                ),
                limit=5
            ).points
            
            # Check for high similarity (>0.95) with different IDs
            for result in search_result:
                if result.id != memory.id and result.score > 0.95:
                    if result.id not in processed_ids:
                        duplicates.append({
                            "memory1_id": memory.id,
                            "memory2_id": result.id,
                            "similarity": result.score,
                            "content1": _get_memory_preview(memory.payload),
                            "content2": _get_memory_preview(result.payload),
                            "action": "merge or delete"
                        })
                        processed_ids.add(memory.id)
                        processed_ids.add(result.id)
                        break
        
        except Exception as e:
            logger.warning(f"Duplicate search error for {memory.id}: {e}")
            continue
    
    return duplicates[:20]  # Limit to top 20


def _find_low_quality(memories: List) -> List[Dict]:
    """
    Identifies memories with quality issues.
    """
    
    low_quality = []
    
    for memory in memories:
        payload = memory.payload
        issues = []
        
        # Check caption length (too short)
        caption = payload.get("caption") or payload.get("transcript") or payload.get("content", "")
        if len(caption) < 20:
            issues.append("Caption too short")
        
        # Generic captions
        generic_phrases = ["a person", "someone", "an image", "a photo", "a video"]
        if any(phrase in caption.lower() for phrase in generic_phrases):
            issues.append("Generic description")
        
        # Missing sentiment for audio
        if payload.get("type") == "audio" and not payload.get("sentiment"):
            issues.append("Missing sentiment")
        
        if issues:
            low_quality.append({
                "memory_id": memory.id,
                "type": payload.get("type"),
                "issues": issues,
                "preview": caption[:100],
                "action": "re-analyze or edit"
            })
    
    return low_quality[:30]


def _find_missing_metadata(memories: List) -> List[Dict]:
    """
    Finds memories with missing tags or locations.
    """
    
    missing = []
    
    for memory in memories:
        payload = memory.payload
        mem_type = payload.get("type", "")
        issues = []
        
        # Images/videos should have people tags
        if mem_type in ["image", "video"]:
            person_tags = payload.get("person_tags", [])
            if not person_tags or len(person_tags) == 0:
                issues.append("Missing people tags")
        
        # Check for location
        if not payload.get("location"):
            issues.append("Missing location")
        
        # Check for milestone flag on significant dates
        timestamp = payload.get("timestamp", 0)
        if timestamp > 0:
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            # Birthday, anniversary, holiday patterns
            # (simplified check - real implementation would use patient birthday data)
            if dt.day == 1 and dt.month == 1:  # New Year
                if not payload.get("milestone"):
                    issues.append("Potential milestone not flagged")
        
        if issues:
            missing.append({
                "memory_id": memory.id,
                "type": mem_type,
                "issues": issues,
                "action": "add metadata"
            })
    
    return missing[:30]


def _find_orphaned_media(memories: List) -> List[Dict]:
    """
    Finds memories with broken media references.
    """
    
    orphaned = []
    
    for memory in memories:
        payload = memory.payload
        
        # Check for video paths that don't exist
        if payload.get("type") == "video":
            video_path = payload.get("video_path")
            if video_path:
                import os
                if not os.path.exists(video_path):
                    orphaned.append({
                        "memory_id": memory.id,
                        "type": "video",
                        "issue": "Video file not found",
                        "path": video_path,
                        "action": "delete or restore"
                    })
    
    return orphaned


def _generate_cleanup_recommendations(
    duplicates: List,
    low_quality: List,
    missing_metadata: List,
    orphaned: List
) -> List[Dict]:
    """
    Generates prioritized cleanup recommendations.
    """
    
    recommendations = []
    
    if duplicates:
        recommendations.append({
            "priority": "high",
            "category": "duplicates",
            "message": f"Found {len(duplicates)} potential duplicates. Review and merge/delete.",
            "count": len(duplicates)
        })
    
    if low_quality:
        recommendations.append({
            "priority": "medium",
            "category": "quality",
            "message": f"{len(low_quality)} memories have quality issues. Consider re-analyzing.",
            "count": len(low_quality)
        })
    
    if missing_metadata:
        recommendations.append({
            "priority": "low",
            "category": "metadata",
            "message": f"{len(missing_metadata)} memories missing tags or locations.",
            "count": len(missing_metadata)
        })
    
    if orphaned:
        recommendations.append({
            "priority": "high",
            "category": "orphaned",
            "message": f"{len(orphaned)} memories have broken media references.",
            "count": len(orphaned)
        })
    
    return recommendations


def _get_memory_preview(payload: dict) -> str:
    """
    Gets a short preview of memory content.
    """
    content = payload.get("caption") or payload.get("transcript") or payload.get("content", "")
    return content[:100]
