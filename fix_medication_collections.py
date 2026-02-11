"""
Fix Medication Collections - Recreate with proper indexes

Run this script to fix the missing indexes in medication_events collection.
This will delete and recreate the collection with all required indexes.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 70)
print("LifeLens Medication Collections Fix")
print("=" * 70)
print()
print("This will recreate the medication_events collection with proper indexes.")
print("⚠️  WARNING: Any existing medication events will be lost!")
print()

response = input("Do you want to continue? (yes/no): ")

if response.lower() != "yes":
    print("Aborted.")
    sys.exit(0)

print()
print("Connecting to Qdrant...")

from lifelens.qdrant.client import get_qdrant_client
from qdrant_client.http import models
from lifelens.config import VECTOR_SIZE

try:
    client = get_qdrant_client()
    print("✅ Connected to Qdrant")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

print()
print("Deleting old medication_events collection...")

try:
    client.delete_collection("medication_events")
    print("✅ Deleted old collection")
except Exception as e:
    print(f"ℹ️  Collection may not exist: {e}")

print()
print("Creating new medication_events collection with proper indexes...")

try:
    # Create collection
    client.create_collection(
        collection_name="medication_events",
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        )
    )
    print("✅ Collection created")
    
    # Create all required indexes
    indexes = [
        ("patient_id", models.PayloadSchemaType.KEYWORD),
        ("medication_id", models.PayloadSchemaType.KEYWORD),
        ("timestamp", models.PayloadSchemaType.FLOAT),  # Unix timestamp
        ("status", models.PayloadSchemaType.KEYWORD),
        ("dose_time", models.PayloadSchemaType.KEYWORD),
        ("dose_date", models.PayloadSchemaType.KEYWORD),
    ]
    
    for field_name, field_type in indexes:
        try:
            client.create_payload_index(
                collection_name="medication_events",
                field_name=field_name,
                field_schema=field_type
            )
            print(f"✅ Created index: {field_name}")
        except Exception as e:
            print(f"❌ Failed to create index {field_name}: {e}")
    
    print()
    print("=" * 70)
    print("✅ SUCCESS!")
    print("=" * 70)
    print()
    print("The medication_events collection has been recreated with all indexes.")
    print()
    print("Next steps:")
    print("1. Restart the medication scheduler service")
    print("2. The Streamlit app will work correctly now")
    print("3. Test by clicking Taken/Skip buttons")
    print()
    
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)
