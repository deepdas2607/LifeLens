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

        # Create type index for filtering
        try:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION_NAME,
                field_name="type",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("Created type index for filtering.")
        except Exception as idx_error:
            logging.info(f"type index status: {idx_error}")
        
        # Create person_tags text index for person search
        try:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION_NAME,
                field_name="person_tags",
                field_schema=models.TextIndexParams(
                    type=models.TextIndexType.TEXT,
                    tokenizer=models.TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=20,
                    lowercase=True
                )
            )
            logging.info("Created person_tags text index for filtering.")
        except Exception as idx_error:
            logging.info(f"person_tags index status: {idx_error}")
            
    except Exception as e:
        logging.error(f"Failed to check or create collection: {e}")
        raise e

def create_user_collection_if_not_exists(client: QdrantClient):
    """
    Creates the Qdrant collection for LifeLens Users.
    Uses a dummy vector size of 1 as we primarily use payload filtering for auth.
    """
    from lifelens.config import QDRANT_USER_COLLECTION_NAME
    try:
        collections = client.get_collections()
        existing_collections = [c.name for c in collections.collections]

        if QDRANT_USER_COLLECTION_NAME not in existing_collections:
            logging.info(f"Creating collection '{QDRANT_USER_COLLECTION_NAME}'...")
            client.create_collection(
                collection_name=QDRANT_USER_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=1, # Minimal vector size since we don't do semantic search on users yet
                    distance=models.Distance.DOT
                )
            )
            logging.info(f"Collection '{QDRANT_USER_COLLECTION_NAME}' created successfully.")
        
        # Create username index for fast lookup
        try:
            client.create_payload_index(
                collection_name=QDRANT_USER_COLLECTION_NAME,
                field_name="username",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except:
            pass
            
    except Exception as e:
        logging.error(f"Failed to create user collection: {e}")
        # Don't raise, just log, so app doesn't crash if Qdrant is down (we have JSON fallback)


def create_mood_collections_if_not_exist(client: QdrantClient):
    """
    Creates dedicated Qdrant collections for Mood Intelligence Agent:
    - mood_events: Time-series mood data
    - mood_alerts: Alert decisions and history
    - mood_feedback: Learning loop for tuning thresholds
    """
    try:
        collections = client.get_collections()
        existing_collections = [c.name for c in collections.collections]
        
        # Create mood_events collection
        if "mood_events" not in existing_collections:
            logging.info("Creating collection 'mood_events'...")
            client.create_collection(
                collection_name="mood_events",
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logging.info("Collection 'mood_events' created successfully.")
            
            # Create indexes for mood_events
            client.create_payload_index(
                collection_name="mood_events",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="mood_events",
                field_name="timestamp",
                field_schema=models.PayloadSchemaType.DATETIME
            )
            client.create_payload_index(
                collection_name="mood_events",
                field_name="mood",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("Indexes created for mood_events.")
        
        # Create mood_alerts collection
        if "mood_alerts" not in existing_collections:
            logging.info("Creating collection 'mood_alerts'...")
            client.create_collection(
                collection_name="mood_alerts",
                vectors_config=models.VectorParams(
                    size=1,  # Minimal vector, focus on payload
                    distance=models.Distance.DOT
                )
            )
            logging.info("Collection 'mood_alerts' created successfully.")
            
            # Create indexes for mood_alerts
            client.create_payload_index(
                collection_name="mood_alerts",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="mood_alerts",
                field_name="timestamp",
                field_schema=models.PayloadSchemaType.DATETIME
            )
            client.create_payload_index(
                collection_name="mood_alerts",
                field_name="notified",
                field_schema=models.PayloadSchemaType.BOOL
            )
            logging.info("Indexes created for mood_alerts.")
        
        # Create mood_feedback collection
        if "mood_feedback" not in existing_collections:
            logging.info("Creating collection 'mood_feedback'...")
            client.create_collection(
                collection_name="mood_feedback",
                vectors_config=models.VectorParams(
                    size=1,  # Minimal vector, focus on payload
                    distance=models.Distance.DOT
                )
            )
            logging.info("Collection 'mood_feedback' created successfully.")
            
            # Create indexes for mood_feedback
            client.create_payload_index(
                collection_name="mood_feedback",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="mood_feedback",
                field_name="alert_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("Indexes created for mood_feedback.")
            
    except Exception as e:
        logging.error(f"Failed to create mood collections: {e}")
        raise e


def create_medication_collections_if_not_exist(client: QdrantClient):
    """
    Creates dedicated Qdrant collections for Medication Tracking System:
    - medications: Active prescriptions and schedules
    - medication_events: Adherence log (taken/skipped/missed)
    - medication_insights: Nightly analytics and alerts
    """
    try:
        collections = client.get_collections()
        existing_collections = [c.name for c in collections.collections]
        
        # Create medications collection
        if "medications" not in existing_collections:
            logging.info("Creating collection 'medications'...")
            client.create_collection(
                collection_name="medications",
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logging.info("Collection 'medications' created successfully.")
        
        # Create indexes for medications (even if collection exists, ensure indexes are there)
        try:
            client.create_payload_index(
                collection_name="medications",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            logging.info(f"patient_id index for medications: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medications",
                field_name="medication_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("medication_id index created for medications.")
        except Exception as e:
            logging.info(f"medication_id index for medications: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medications",
                field_name="active",
                field_schema=models.PayloadSchemaType.BOOL
            )
        except Exception as e:
            logging.info(f"active index for medications: {e}")
        
        # Create medication_events collection
        if "medication_events" not in existing_collections:
            logging.info("Creating collection 'medication_events'...")
            client.create_collection(
                collection_name="medication_events",
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logging.info("Collection 'medication_events' created successfully.")
        
        # Create indexes for medication_events (even if collection exists)
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            logging.info(f"patient_id index for medication_events: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name="medication_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("medication_id index created for medication_events.")
        except Exception as e:
            logging.info(f"medication_id index for medication_events: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name="timestamp",
                field_schema=models.PayloadSchemaType.FLOAT  # Changed from DATETIME to FLOAT for Unix timestamps
            )
        except Exception as e:
            logging.info(f"timestamp index for medication_events: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name="status",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            logging.info(f"status index for medication_events: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name="dose_time",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            logging.info(f"dose_time index for medication_events: {e}")
        
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name="dose_date",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            logging.info(f"dose_date index for medication_events: {e}")
        
        # Create medication_insights collection
        if "medication_insights" not in existing_collections:
            logging.info("Creating collection 'medication_insights'...")
            client.create_collection(
                collection_name="medication_insights",
                vectors_config=models.VectorParams(
                    size=1,  # Minimal vector, focus on payload
                    distance=models.Distance.DOT
                )
            )
            logging.info("Collection 'medication_insights' created successfully.")
            
            # Create indexes for medication_insights
            client.create_payload_index(
                collection_name="medication_insights",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="medication_insights",
                field_name="timestamp",
                field_schema=models.PayloadSchemaType.DATETIME
            )
            client.create_payload_index(
                collection_name="medication_insights",
                field_name="verdict",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("Indexes created for medication_insights.")
            
    except Exception as e:
        logging.error(f"Failed to create medication collections: {e}")
        raise e


def create_agent_decisions_collection_if_not_exist(client: QdrantClient):
    """
    Creates dedicated Qdrant collection for Agent Decision Logging (multiagent.md compliance):
    - agent_decisions: Logs all agent plans, replans, verdicts, and trigger decisions
    
    This is the "meta-memory" that makes agents observable and debuggable.
    """
    try:
        collections = client.get_collections()
        existing_collections = [c.name for c in collections.collections]
        
        # Create agent_decisions collection
        if "agent_decisions" not in existing_collections:
            logging.info("Creating collection 'agent_decisions'...")
            client.create_collection(
                collection_name="agent_decisions",
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logging.info("Collection 'agent_decisions' created successfully.")
            
            # Create indexes for agent_decisions
            client.create_payload_index(
                collection_name="agent_decisions",
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="agent_decisions",
                field_name="agent",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="agent_decisions",
                field_name="timestamp",
                field_schema=models.PayloadSchemaType.FLOAT  # Unix timestamp
            )
            client.create_payload_index(
                collection_name="agent_decisions",
                field_name="verdict",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            client.create_payload_index(
                collection_name="agent_decisions",
                field_name="attempt",
                field_schema=models.PayloadSchemaType.INTEGER
            )
            client.create_payload_index(
                collection_name="agent_decisions",
                field_name="session_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logging.info("Indexes created for agent_decisions.")
            
    except Exception as e:
        logging.error(f"Failed to create agent_decisions collection: {e}")
        raise e
