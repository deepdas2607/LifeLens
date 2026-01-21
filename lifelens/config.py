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
VECTOR_SIZE = 768  # Gemini text-embedding-004
DISTANCE_METRIC = "Cosine"

# Paths
PROCESS_DIR = "processed_data"
