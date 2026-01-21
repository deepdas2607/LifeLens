import streamlit as st
from qdrant_client import QdrantClient
from lifelens.config import QDRANT_URL, QDRANT_API_KEY

@st.cache_resource
def get_qdrant_client() -> QdrantClient:
    """
    Initializes and returns a QdrantClient instance.
    Cached by Streamlit to avoid multiple connections.
    """
    if not QDRANT_URL:
        raise ValueError("QDRANT_URL is not set in environment variables.")
    
    # Qdrant Cloud connection with SSL verification disabled
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        verify=False  # Disable SSL verification for self-signed certificates
    )
    return client
