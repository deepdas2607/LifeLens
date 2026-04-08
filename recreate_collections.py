import os
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv
from lifelens.config import QDRANT_COLLECTION_NAME, VECTOR_SIZE

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recreate_collections():
    # Load .env
    load_dotenv('lifelens/.env')
    
    url = os.getenv('QDRANT_URL')
    api_key = os.getenv('QDRANT_API_KEY')
    
    if not url:
        logger.error("QDRANT_URL not found in lifelens/.env")
        return

    client = QdrantClient(url=url, api_key=api_key)
    
    logger.info(f"Checking collection: {QDRANT_COLLECTION_NAME}")
    
    # Check if collection exists
    try:
        collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
        current_size = collection_info.config.params.vectors.size
        logger.info(f"Current collection vector size: {current_size}")
        
        if current_size != VECTOR_SIZE:
            logger.warning(f"Vector size mismatch! Current: {current_size}, Expected: {VECTOR_SIZE}")
            logger.info(f"Deleting and recreating collection '{QDRANT_COLLECTION_NAME}'...")
            client.delete_collection(QDRANT_COLLECTION_NAME)
        else:
            logger.info("Vector size matches. No need to recreate.")
            return
            
    except Exception as e:
        logger.info(f"Collection does not exist or error: {e}")

    # Create collection
    logger.info(f"Creating collection '{QDRANT_COLLECTION_NAME}' with size {VECTOR_SIZE}...")
    client.create_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        )
    )
    
    # Create indexes
    logger.info("Creating payload indexes...")
    client.create_payload_index(QDRANT_COLLECTION_NAME, "patient_id", models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(QDRANT_COLLECTION_NAME, "type", models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(QDRANT_COLLECTION_NAME, "category", models.PayloadSchemaType.KEYWORD)
    
    logger.info("Successfully recreated collections!")

if __name__ == "__main__":
    recreate_collections()
