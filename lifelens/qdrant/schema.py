from qdrant_client import QdrantClient
from qdrant_client.http import models
from lifelens.config import QDRANT_COLLECTION_NAME, VECTOR_SIZE, DISTANCE_METRIC
import logging

def create_collection_if_not_exists(client: QdrantClient):
    """
    Creates the Qdrant collection for LifeLens if it does not already exist.
    Also ensures patient_id index exists for filtering.
    """
    try:
        collections = client.get_collections()
        existing_collections = [c.name for c in collections.collections]

        if QDRANT_COLLECTION_NAME not in existing_collections:
            logging.info(f"Creating collection '{QDRANT_COLLECTION_NAME}'...")
            client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logging.info(f"Collection '{QDRANT_COLLECTION_NAME}' created successfully.")
        else:
            logging.info(f"Collection '{QDRANT_COLLECTION_NAME}' already exists.")
        
        # Create or update patient_id index for filtering
        try:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION_NAME,
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("Created patient_id index for filtering.")
        except Exception as idx_error:
            # Index might already exist
            logging.info(f"patient_id index status: {idx_error}")
            
    except Exception as e:
        logging.error(f"Failed to check or create collection: {e}")
        raise e
