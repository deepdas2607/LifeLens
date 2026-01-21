import google.generativeai as genai
from qdrant_client import QdrantClient
from lifelens.config import QDRANT_COLLECTION_NAME, GEMINI_API_KEY
from qdrant_client.http import models
import logging

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_embedding(text: str):
    """
    Generates embedding using Gemini API (Query mode).
    """
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
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
    
    Args:
        client: QdrantClient instance
        query: User query string
        filters: Optional dictionary for filtering (e.g., {'timestamp': {'gte': 12345}}})
        top_k: Number of results to return
        patient_id: Filter by patient ID
    
    Returns:
        List of formatted search results
    """
    
    # Generate Query Embedding
    query_vector = get_embedding(query)
    
    # Construct Filter
    qdrant_filter = None
    conditions = []
    
    # Add patient_id filter
    if patient_id:
        conditions.append(
            models.FieldCondition(
                key="patient_id",
                match=models.MatchValue(value=patient_id)
            )
        )
    
    # Add timestamp filters
    if filters and 'timestamp' in filters:
        conditions.append(
            models.FieldCondition(
                key="timestamp",
                range=models.Range(**filters['timestamp'])
            )
        )
    
    if conditions:
        qdrant_filter = models.Filter(must=conditions)

    # Perform Search using query_points
    search_result = client.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=top_k,
        with_payload=True
    ).points
    
    # Parse Results
    results = []
    for hit in search_result:
        results.append({
            "score": hit.score,
            "type": hit.payload.get("type"),
            "caption": hit.payload.get("caption"),
            "transcript": hit.payload.get("transcript"),
            "content": hit.payload.get("content"),
            "timestamp": hit.payload.get("timestamp"),
            "sentiment": hit.payload.get("sentiment"),
            "person_tags": hit.payload.get("person_tags"),
            "source_image_base64": hit.payload.get("source_image_base64"),
            "source_audio_base64": hit.payload.get("source_audio_base64")
        })
        
    return results
