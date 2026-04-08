"""
Check Qdrant collections and verify where extension data is stored
"""
import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

print(f"Connecting to Qdrant at: {QDRANT_URL}")

try:
    # Connect to Qdrant
    if QDRANT_API_KEY:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, verify=False)
    else:
        client = QdrantClient(url=QDRANT_URL)
    
    # Get all collections
    collections = client.get_collections()
    print("\n✅ Connected to Qdrant!")
    print(f"\nFound {len(collections.collections)} collection(s):")
    
    for collection in collections.collections:
        print(f"\n📦 Collection: {collection.name}")
        
        # Get collection info
        info = client.get_collection(collection.name)
        print(f"   Points count: {info.points_count}")
        print(f"   Vector size: {info.config.params.vectors.size}")
        
        # Get a sample point
        if info.points_count > 0:
            sample = client.scroll(
                collection_name=collection.name,
                limit=1,
                with_payload=True,
                with_vectors=False
            )[0]
            
            if sample:
                print(f"   Sample payload keys: {list(sample[0].payload.keys())}")
                if "patient_id" in sample[0].payload:
                    print(f"   Sample patient_id: {sample[0].payload['patient_id']}")
                if "type" in sample[0].payload:
                    print(f"   Sample type: {sample[0].payload['type']}")
                if "content" in sample[0].payload:
                    content = sample[0].payload['content'][:100]
                    print(f"   Sample content: {content}...")

    # Check the expected collection
    expected_collection = "lifelens_memory"
    print(f"\n{'='*60}")
    print(f"Expected collection for extension: {expected_collection}")
    
    collection_names = [c.name for c in collections.collections]
    if expected_collection in collection_names:
        print(f"✅ Collection '{expected_collection}' exists!")
        
        # Get recent points
        info = client.get_collection(expected_collection)
        print(f"\nTotal memories stored: {info.points_count}")
        
        if info.points_count > 0:
            # Get last 5 memories
            recent = client.scroll(
                collection_name=expected_collection,
                limit=5,
                with_payload=True,
                with_vectors=False
            )[0]
            
            print(f"\nRecent {len(recent)} memories:")
            for i, point in enumerate(recent, 1):
                payload = point.payload
                print(f"\n{i}. Type: {payload.get('type', 'unknown')}")
                print(f"   Patient: {payload.get('patient_id', 'unknown')}")
                print(f"   Timestamp: {payload.get('timestamp', 'unknown')}")
                if 'content' in payload:
                    print(f"   Content: {payload['content'][:100]}...")
                if 'source' in payload:
                    print(f"   Source: {payload['source']}")
        else:
            print("\n⚠️ No memories found in collection!")
            print("   This means:")
            print("   1. Extension data is not being saved, OR")
            print("   2. You haven't saved anything yet")
    else:
        print(f"❌ Collection '{expected_collection}' does NOT exist!")
        print(f"   Available: {collection_names}")
        
except Exception as e:
    print(f"\n❌ Error connecting to Qdrant: {e}")
    print("\nPossible issues:")
    print("1. Qdrant is not running")
    print("2. Wrong URL (make sure QDRANT_URL is set in .env)")
    print("3. Network connection issue")
