"""
Quick check of mood system status
"""
import sys
sys.path.insert(0, '.')

from lifelens.qdrant.client import get_qdrant_client
from lifelens.utils.ntfy_notifications import send_mood_alert

print("="*70)
print("  MOOD SYSTEM STATUS CHECK")
print("="*70)

# Connect to Qdrant
client = get_qdrant_client()
print("\n✓ Connected to Qdrant")

# Check mood events
events = client.scroll(
    collection_name="mood_events",
    limit=20,
    with_payload=True
)[0]
print(f"✓ Found {len(events)} mood events in database")

if events:
    print("\nRecent mood events:")
    for event in events[:5]:
        payload = event.payload
        print(f"  • {payload.get('mood', 'unknown'):12s} "
              f"({payload.get('mood_score', 0):+.2f}) "
              f"- {payload.get('patient_id', 'unknown'):20s} "
              f"at {payload.get('timestamp', 'unknown')[:10]}")

# Check alerts
alerts = client.scroll(
    collection_name="mood_alerts",
    limit=10,
    with_payload=True
)[0]
print(f"\n✓ Found {len(alerts)} alerts in database")

if alerts:
    print("\nRecent alerts:")
    for alert in alerts[:3]:
        payload = alert.payload
        print(f"  • {payload.get('verdict', 'unknown'):8s} "
              f"({payload.get('risk_score', 0)*100:.1f}%) "
              f"- {payload.get('patient_id', 'unknown')}")

# Test notification
print("\n" + "="*70)
print("  TESTING NOTIFICATION")
print("="*70)

test_result = send_mood_alert(
    patient_id="test_patient_mood_demo",
    summary="5-day negative mood streak detected (TEST)",
    risk_score=0.75
)

if test_result:
    print("\n✅ TEST NOTIFICATION SENT SUCCESSFULLY!")
    print("\nCheck your ntfy topic:")
    print("👉 https://ntfy.sh/lifelens-mood-test_patient_mood_demo")
else:
    print("\n❌ Notification failed - check logs above")

print("\n" + "="*70)
print("  TO VIEW IN DASHBOARD:")
print("="*70)
print("\n1. Start: streamlit run lifelens/app.py")
print("2. Login: test_patient / demo123")
print("3. Navigate to Dashboard page")
print("4. Scroll to 'Mood Intelligence Insights' section")
print("\n" + "="*70)
