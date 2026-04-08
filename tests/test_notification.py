"""
Test mood alert notification directly
"""
import sys
import os
# Add parent directory to path to import lifelens
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lifelens.utils.ntfy_notifications import send_mood_alert
from lifelens.config import NTFY_MOOD_TOPIC_URL

print("="*70)
print("  TESTING MOOD ALERT NOTIFICATION")
print("="*70)

print(f"\nTarget topic: {NTFY_MOOD_TOPIC_URL}")
print("\nSending test alert...")

result = send_mood_alert(
    patient_id="patient_1",
    summary="5-day negative mood decline detected - Manual test from terminal",
    risk_score=0.75
)

if result:
    print("\n[SUCCESS] NOTIFICATION SENT SUCCESSFULLY!")
    print("\nCheck your ntfy subscription:")
    print(f"[URL] {NTFY_MOOD_TOPIC_URL}")
    print("\nYou should receive a notification with:")
    print("  [INFO] Title: Mood Alert - Patient patient_1")
    print("  [INFO] Risk Level: 75%")
    print("  [INFO] Tags: warning, heart, medical_symbol emojis")
else:
    print("\n[FAIL] NOTIFICATION FAILED!")
    print("Check the error logs above")

print("\n" + "="*70)
