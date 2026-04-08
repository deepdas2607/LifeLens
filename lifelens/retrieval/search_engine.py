import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')
import google.generativeai as genai
from qdrant_client import QdrantClient
from lifelens.config import QDRANT_COLLECTION_NAME, GEMINI_API_KEY
from qdrant_client.http import models
import logging
from typing import List

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_embedding(text: str):
    """
    Generates embedding using Gemini API (Query mode).
    """
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return result['embedding']
    except Exception as e:
        logging.error(f"Failed to generate embedding: {e}")
        raise e

def search_memories(client: QdrantClient, query: str, filters: dict = None, top_k: int = 10, patient_id: str = None):
    """
    Search for memories in Qdrant based on semantic similarity using Gemini Embeddings.
    Enhanced with person and location awareness.
    
    Args:
        client: QdrantClient instance
        query: User query string
        filters: Optional dictionary for filtering (e.g., {'timestamp': {'gte': 12345}})
        top_k: Number of results to return
        patient_id: Filter by patient ID
    
    Returns:
        List of formatted search results
    """
    
    # Generate Query Embedding
    query_vector = get_embedding(query)
    
    # Detect if query is about a person or location
    query_lower = query.lower()
    person_keywords = ['who is', 'tell me about', 'show me', 'find', 'about']
    location_keywords = ['where', 'location', 'place', 'at']
    
    is_person_query = any(keyword in query_lower for keyword in person_keywords)
    is_location_query = any(keyword in query_lower for keyword in location_keywords)
    
    # Construct Filter
    qdrant_filter = None
    conditions = []
    should_conditions = []  # For OR conditions
    
    # Add patient_id filter
    if patient_id:
        conditions.append(
            models.FieldCondition(
                key="patient_id",
                match=models.MatchValue(value=patient_id)
            )
        )
        logging.info(f"Filtering by patient_id: {patient_id}")
    else:
        logging.warning("No patient_id provided for search!")
    
    # Add timestamp filters
    if filters and 'timestamp' in filters:
        conditions.append(
            models.FieldCondition(
                key="timestamp",
                range=models.Range(**filters['timestamp'])
            )
        )
    
    # Add mood/sentiment filters
    if filters and 'mood' in filters:
        mood_list = filters['mood']
        if mood_list:
            # Use should (OR) for multiple moods
            for mood in mood_list:
                should_conditions.append(
                    models.FieldCondition(
                        key="sentiment",
                        match=models.MatchValue(value=mood)
                    )
                )
    
    # Add type filters
    if filters and 'type' in filters:
        type_list = filters['type']
        if type_list:
            # Use should (OR) for multiple types
            for mem_type in type_list:
                should_conditions.append(
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value=mem_type)
                    )
                )
    
    # Enhanced: If asking about a person, try to match person_tags
    # Extract potential name from query (simple heuristic)
    if is_person_query:
        # Try to extract name - look for capitalized words that aren't common words
        import re
        words = query.split()
        potential_names = [w for w in words if w[0].isupper() and w.lower() not in 
                          ['who', 'is', 'tell', 'me', 'about', 'show', 'find', 'the', 'a', 'an']]
        
        if potential_names:
            # Use should (OR) to match any of the potential names in person_tags
            for name in potential_names:
                should_conditions.append(
                    models.FieldCondition(
                        key="person_tags",
                        match=models.MatchText(text=name)
                    )
                )
    
    # Build final filter
    if conditions or should_conditions:
        filter_params = {}
        if conditions:
            filter_params["must"] = conditions
        if should_conditions:
            filter_params["should"] = should_conditions
        qdrant_filter = models.Filter(**filter_params)

    # Perform Search using query_points
    search_result = client.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=top_k * 2,  # Get more results for hybrid filtering
        with_payload=True
    ).points
    
    # Parse Results
    results = []
    keywords = _extract_keywords(query)  # Extract keywords for hybrid search
    
    for hit in search_result:
        result = {
            "score": hit.score,
            "type": hit.payload.get("type"),
            "caption": hit.payload.get("caption"),
            "transcript": hit.payload.get("transcript"),
            "content": hit.payload.get("content"),
            "analysis": hit.payload.get("analysis"),  # For video
            "timestamp": hit.payload.get("timestamp"),
            "sentiment": hit.payload.get("sentiment"),
            "person_tags": hit.payload.get("person_tags"),
            "location": hit.payload.get("location"),
            "source_image_base64": hit.payload.get("source_image_base64"),
            "source_audio_base64": hit.payload.get("source_audio_base64"),
            "video_path": hit.payload.get("video_path")
        }
        
        # Hybrid scoring: Boost if keywords match in text content
        text_fields = [
            result.get("caption", ""),
            result.get("transcript", ""),
            result.get("content", ""),
            result.get("analysis", ""),
            result.get("person_tags", "")
        ]
        text_content = " ".join(str(f) for f in text_fields if f).lower()
        
        keyword_boost = 0
        for keyword in keywords:
            if keyword.lower() in text_content:
                keyword_boost += 0.1  # Boost 0.1 per keyword match
        
        result["score"] = min(1.0, result["score"] + keyword_boost)  # Cap at 1.0
        result["keyword_matches"] = [kw for kw in keywords if kw.lower() in text_content]
        
        results.append(result)
    
    # Sort by hybrid score and limit to top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]
    
    logging.info(f"Search returned {len(results)} results (with keyword boosting)")
    
    return results


def _extract_keywords(query: str) -> List[str]:
    """
    Extract important keywords from query for hybrid search.
    Ignores common stop words.
    """
    stop_words = {
        'tell', 'me', 'about', 'what', 'when', 'where', 'who', 'how', 'show',
        'find', 'from', 'my', 'memories', 'the', 'a', 'an', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was',
        'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did'
    }
    
    words = query.split()
    keywords = [word for word in words if word.lower() not in stop_words and len(word) > 2]
    
    return keywords
