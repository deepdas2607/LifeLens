"""
Create mood demo data for patient1 (default patient)
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from lifelens.qdrant.client import get_qdrant_client
from lifelens.ingestion.upsert_memory import upsert_memory

print("Creating mood data for patient1...")

client = get_qdrant_client()
patient_id = "patient_1"

# 5-day declining mood trend
moods = [
    ("anxious", "I'm feeling a bit anxious today. Not sure what's bothering me."),
    ("frustrated", "I'm frustrated with how things are going. Nothing seems to work."),
    ("sad", "Feeling really sad today. Everything seems overwhelming."),
    ("angry", "I'm so angry at everything. Why does this keep happening?"),
    ("depressed", "I can't remember the last time I felt happy. Everything is darkness.")
]

for i, (mood, text) in enumerate(moods):
    timestamp_dt = datetime.utcnow() - timedelta(days=5-i)
    timestamp_str = timestamp_dt.isoformat() + "Z"
    
    # Create memory data
    data = {
        "patient_id": patient_id,
        "transcript": text,
        "mood": mood,  # This triggers mood event storage
        "sentiment": mood.capitalize(),
        "base64": "",  # Empty = no audio preview (mood data only)
        "audio_base64": "",
        "timestamp": timestamp_str  # Backdated timestamp
    }
    
    # Upsert memory (will auto-create mood event)
    upsert_memory(client, "audio", data)
    
    print(f"✓ Created {mood} mood memory (Day -{5-i})")

print(f"\n✅ 5 mood memories created for patient_1")
print("\n📊 Now you can:")
print("1. Login as: patient1 / patient123")
print("2. Go to Dashboard")
print("3. See mood intelligence data!")
