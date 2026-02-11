import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.qdrant.client import get_qdrant_client
from lifelens.qdrant.schema import create_collection_if_not_exists

print("Applying Qdrant Schema Updates...")
try:
    client = get_qdrant_client()
    create_collection_if_not_exists(client)
    print("✅ Schema updated successfully. 'type' index created.")
except Exception as e:
    print(f"❌ Error: {e}")
