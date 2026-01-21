from qdrant_client import QdrantClient
from lifelens.config import QDRANT_COLLECTION_NAME
from datetime import datetime, timedelta
from collections import Counter
import pandas as pd

def get_memory_stats(client: QdrantClient, patient_id: str):
    """Get comprehensive memory statistics for a patient."""
    
    # Fetch all memories for patient
    results = client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=1000,
        with_payload=True,
        with_vectors=False,
        scroll_filter={"must": [{"key": "patient_id", "match": {"value": patient_id}}]}
    )[0]
    
    if not results:
        return None
    
    # Extract data
    memories = [point.payload for point in results]
    
    # Total counts
    total_count = len(memories)
    type_counts = Counter([m.get("type") for m in memories])
    
    # Mood distribution
    sentiments = [m.get("sentiment") for m in memories if m.get("sentiment")]
    mood_distribution = Counter(sentiments)
    
    # Activity by day
    timestamps = [m.get("timestamp", 0) for m in memories]
    dates = [datetime.fromtimestamp(ts).date() for ts in timestamps]
    daily_counts = Counter(dates)
    
    # Memory streak (consecutive days with uploads)
    sorted_dates = sorted(set(dates), reverse=True)
    streak = 0
    if sorted_dates:
        current_date = datetime.now().date()
        for date in sorted_dates:
            if (current_date - date).days == streak:
                streak += 1
            else:
                break
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_count = sum(1 for ts in timestamps if datetime.fromtimestamp(ts) > week_ago)
    
    return {
        "total_count": total_count,
        "type_counts": dict(type_counts),
        "mood_distribution": dict(mood_distribution),
        "daily_counts": daily_counts,
        "streak": streak,
        "recent_count": recent_count,
        "memories": memories
    }

def get_activity_dataframe(daily_counts):
    """Convert daily counts to DataFrame for charting."""
    if not daily_counts:
        return pd.DataFrame()
    
    df = pd.DataFrame([
        {"Date": date, "Count": count}
        for date, count in daily_counts.items()
    ])
    df = df.sort_values("Date")
    return df
