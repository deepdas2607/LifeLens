"""
LifeLens Background Reminder Script
This script runs independently of the Streamlit app to send engagement reminders.
Usage: python scripts/background_reminder.py
"""

import time
import os
import sys
from datetime import datetime

# Add project root (parent of lifelens folder) to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from lifelens.utils.ntfy_notifications import send_ntfy
from lifelens.config import NTFY_TOPIC_URL

# For demo purposes, we send a reminder every 5 minutes
# In production, this would be 24 hours or based on user activity
INTERVAL_SECONDS = 300 
APP_URL = "http://localhost:8501" # Default Streamlit port

def run_reminder_loop():
    print(f"🚀 LifeLens Background Reminder Service Started")
    print(f"📡 Monitoring topic: {NTFY_TOPIC_URL}")
    print(f"⏰ Interval: {INTERVAL_SECONDS / 60} minutes")
    print(f"🔗 App Link: {APP_URL}")
    print("-" * 40)

    try:
        while True:
            now = datetime.now().strftime("%I:%M %p")
            print(f"[{now}] Sending engagement reminder...")
            
            success = send_ntfy(
                title="LifeLens: Time to Remember",
                body="Don't let today's precious moments fade. Capture a quick memory now!",
                priority="high",
                tags="brain,memo,sparkles",
                click_url=APP_URL
            )
            
            if success:
                print("✅ Notification sent successfully.")
            else:
                print("❌ Failed to send notification. Check internet/ntfy topic.")
            
            print(f"💤 Sleeping for {INTERVAL_SECONDS / 60} minutes...")
            time.sleep(INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n🛑 Background service stopped.")

if __name__ == "__main__":
    run_reminder_loop()
