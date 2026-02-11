"""
Patient Medication Page

Interface for patients to view and manage their daily medications.
"""

import streamlit as st
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.session import init_session, is_logged_in, get_current_user, get_active_patient_id
from lifelens.qdrant.client import get_qdrant_client
from lifelens.ui.medication_components import render_patient_medication_list, show_medication_reminder_banner
from lifelens.agents.medication_scheduler import get_upcoming_doses
from lifelens.utils.medication_utils import calculate_adherence_rate, get_medication_history
from datetime import datetime

# Page Config
st.set_page_config(page_title="My Medications", page_icon="💊", layout="wide")

# Apply styles
from lifelens.utils.styles import apply_styles
apply_styles()

# Initialize session
init_session()

# Check authentication
if not is_logged_in():
    st.error("Please log in from the main page.")
    st.stop()

user = get_current_user()
patient_id = get_active_patient_id()

# Prevent family members from accessing this page
if user["role"] == "family":
    st.error("🚫 Access Denied: This page is only for Patients and Caretakers.")
    st.info("👨‍👩‍👧‍👦 Family members can view medication information in the Family Portal.")
    st.stop()

# If user is a patient, use  their own ID
if user["role"] == "patient":
    patient_id = user.get("patient_id")

if not patient_id:
    st.error("No patient ID found. Please contact your caretaker.")
    st.stop()

# Header
st.title("💊 My Medications")
st.markdown(f"**Patient:** {patient_id}")
st.markdown("---")

# Get client
client = get_qdrant_client()

# Check for upcoming reminders (within 5 minutes)
upcoming = get_upcoming_doses(client, patient_id, look_ahead_minutes=5)

if upcoming:
    st.warning(f"You have {len(upcoming)} medication(s) due soon!")
    for dose in upcoming:
        show_medication_reminder_banner(dose)

# Sidebar with quick stats
with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    # 7-day adherence
    adherence_7d = calculate_adherence_rate(client, patient_id, days=7)
    st.metric("7-Day Adherence", f"{adherence_7d*100:.1f}%")
    
    # Recent history
    recent_history = get_medication_history(client, patient_id, days=7)
    taken_count = len([e for e in recent_history if e.get("status") == "taken"])
    st.metric("Doses Taken (7d)", taken_count)
    
    st.markdown("---")
    
    # Logout button
    if st.button("🚪 Logout", width="stretch"):
        from lifelens.auth.session import logout
        logout()
        st.rerun()

# Main content - Today's medications
render_patient_medication_list(client, patient_id)

st.markdown("---")

# Medication history section
with st.expander("📜 Recent History"):
    history = get_medication_history(client, patient_id, days=7)
    
    if history:
        import pandas as pd
        
        # Convert to dataframe
        df_data = []
        for event in history[:20]:  # Show last 20
            df_data.append({
                "Date": datetime.fromtimestamp(event['timestamp']).strftime("%Y-%m-%d"),
                "Time": datetime.fromtimestamp(event['timestamp']).strftime("%H:%M"),
                "Medication": event.get("medication_id", "Unknown")[:15],
                "Status": event.get("status", "").title(),
                "Note": event.get("note", "")[:30]
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No medication history available.")

# Instructions
st.markdown("---")
with st.expander("ℹ️ How to Use"):
    st.markdown("""
    ### Taking Your Medications
    
    1. **Check your medication list** - All medications scheduled for today are shown above
    2. **Take your medication** - When you take a dose, click the "✅ Taken" button
    3. **Skip if needed** - If you need to skip a dose, click "⏭️ Skip" and provide a reason
    4. **Watch for reminders** - You'll receive notifications when it's time to take your medication
    
    ### Status Indicators
    
    - **Upcoming**: Medication will be due soon
    - **Overdue**: Medication should have been taken already (shown in red)
    - **Completed**: Medication has been taken or skipped today
    
    ### Getting Help
    
    If you have questions about your medications, contact your caretaker.
    Call emergency services if you experience serious side effects.
    """)
