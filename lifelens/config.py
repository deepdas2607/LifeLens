import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and URLs
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Service Configuration
QDRANT_COLLECTION_NAME = "lifelens_memory"
QDRANT_USER_COLLECTION_NAME = "lifelens_users"
VECTOR_SIZE = 3072  # Gemini gemini-embedding-001
DISTANCE_METRIC = "Cosine"

# Paths
PROCESS_DIR = "processed_data"

# Auth
JWT_SECRET = os.getenv("JWT_SECRET", "lifelens_super_secret_key_2025")
JWT_ALGORITHM = "HS256"

# Trigger System Configuration
NTFY_TOPIC_URL = os.getenv("NTFY_TOPIC_URL", "https://ntfy.sh/lifelens-caregiver-alerts")
NTFY_MOOD_TOPIC_URL = os.getenv("NTFY_MOOD_TOPIC_URL", "https://ntfy.sh/lifelens-mood-test_patient_mood_demo")
TRIGGER_CHECK_INTERVAL_MINUTES = 2  # How often to check for new triggers (Reduced for demo)
MEMORY_GAP_THRESHOLD_MINUTES = 5    # Trigger if no memories for this long (Reduced for demo)
PHOTO_GAP_THRESHOLD_MINUTES = 10   # Trigger if no photos for this long (Reduced for demo)
TRIGGER_STORAGE_FILE = "triggers.json"

# Multi-Agent System Configuration
PLANNER_MODEL = "llama-3.3-70b-versatile"
CRITIC_MODEL = "llama-3.3-70b-versatile"
MAX_RETRY_ATTEMPTS = 1
AGENTIC_MODE_ENABLED = True  # Toggle for agentic vs legacy flow


