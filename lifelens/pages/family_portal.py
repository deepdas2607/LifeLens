import streamlit as st
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.session import init_session, is_logged_in, get_current_user, get_active_patient_id
from lifelens.qdrant.client import get_qdrant_client
from lifelens.config import QDRANT_COLLECTION_NAME
from lifelens.utils.analytics import get_memory_stats
from lifelens.utils.memory_requests import create_request, get_requests_for_patient
from qdrant_client.http import models
import pandas as pd
import altair as alt
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

# Page Config
st.set_page_config(page_title="Family Portal", page_icon="👨‍👩‍👧‍👦", layout="wide")

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

# Check family access
if user["role"] != "family":
    st.error("Access Denied. This portal is only for Family members.")
    st.stop()

patient_id = get_active_patient_id()

# Patient selector if not selected
if not patient_id:
    st.title("👨‍👩‍👧‍👦 Family Portal")
    st.subheader("Select Patient")
    
    from lifelens.auth.users import get_all_patients
    from lifelens.auth.session import set_active_patient
    
    patients = get_all_patients()
    
    if patients:
        for patient in patients:
            if st.button(f"👤 {patient['full_name']} ({patient['patient_id']})", width="stretch"):
                set_active_patient(patient['patient_id'])
                st.rerun()
    else:
        st.warning("No patients found in the system.")
    
    st.stop()

st.title(f"👨‍👩‍👧‍👦 Family Portal for Patient {patient_id}")
st.markdown(f"**Welcome, {user['full_name']}** (View-Only Access)")

# Logout and patient selector in sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 👤 Session Info")
    st.caption(f"User: {user['full_name']}")
    st.caption(f"Role: {user['role'].title()}")
    st.caption(f"Patient: {patient_id}")
    st.markdown("---")
    
    if st.button("🔄 Change Patient", width="stretch"):
        from lifelens.auth.session import set_active_patient
        set_active_patient(None)
        st.rerun()
    
    if st.button("🚺 Logout", width="stretch", type="primary"):
        from lifelens.auth.session import logout
        logout()
        st.rerun()
    
    # Trigger System Integration
    from lifelens.ui.trigger_components import handle_trigger_lifecycle
    handle_trigger_lifecycle(get_qdrant_client(), patient_id)

st.markdown("---")

# Get client
client = get_qdrant_client()

# Tabs for different sections
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Overview", "📖 Family Recap", "🎉 Milestones", "💊 Medications", "📝 Memory Requests", "📸 Photo Gallery"])

# === TAB 1: OVERVIEW ===
with tab1:
    st.header("Patient Overview")
    
    # Get stats
    stats = get_memory_stats(client, patient_id)
    
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Memories", stats["total_count"])
        
        with col2:
            st.metric("This Week", stats["recent_count"])
        
        with col3:
            st.metric("🔥 Active Days", stats["streak"])
        
        with col4:
            image_count = stats["type_counts"].get("image", 0)
            st.metric("📸 Photos", image_count)
        
        st.markdown("---")
        
        # Recent Activity
        st.subheader("Recent Activity")
        
        # Get recent memories, excluding agent decisions
        recent_results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=10,
            with_payload=True,
            with_vectors=False,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ],
                must_not=[
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="agent_decision")
                    )
                ]
            )
        )[0]
        
        if recent_results:
            for point in sorted(recent_results, key=lambda x: x.payload.get('timestamp', 0), reverse=True):
                p = point.payload
                timestamp = datetime.fromtimestamp(p.get("timestamp", 0)).strftime("%B %d, %Y at %I:%M %p")
                
                with st.expander(f"{p.get('type', 'Memory').upper()} - {timestamp}"):
                    if p.get("caption"):
                        st.write(p["caption"])
                    elif p.get("transcript"):
                        st.write(p["transcript"])
                    elif p.get("content"):
                        st.write(p["content"])
                    elif p.get("analysis"):  # For videos
                        st.write(p["analysis"])
                    
                    if p.get("person_tags"):
                        st.caption(f"👤 People: {p['person_tags']}")
                    
                    if p.get("location"):
                        loc = p["location"]
                        st.caption(f"📍 Location: {loc.get('name', f'{loc['lat']}, {loc['lon']}')}")
        else:
            st.info("No recent activity.")
    else:
        st.warning("No memories found for this patient.")

# === TAB 2: MILESTONES ===
with tab2:
    st.header("🎉 Milestones & Achievements")
    st.caption("Track important moments and achievements")
    
    # Filter memories by type or tags
    if stats and stats["memories"]:
        # Look for achievement-related keywords or explicit categories
        achievements = []
        milestone_keywords = [
            "achievement", "milestone", "award", "celebration", "birthday", 
            "anniversary", "graduation", "wedding", "born", "birth", "win", 
            "won", "prize", "first", "success", "party", "hospital", "doctor"
        ]
        milestone_categories = ["Achievement", "Event", "Milestone", "Family Gathering"]
        
        for mem in stats["memories"]:
            # Check explicit category first
            category = mem.get("category")
            if category in milestone_categories:
                achievements.append(mem)
                continue
                
            # Fallback to keyword search
            content = (mem.get("caption") or mem.get("transcript") or mem.get("content") or "").lower()
            if any(word in content for word in milestone_keywords):
                achievements.append(mem)
        
        if achievements:
            st.write(f"**{len(achievements)} milestones found:**")
            
            for mem in sorted(achievements, key=lambda x: x.get('timestamp', 0), reverse=True):
                timestamp = datetime.fromtimestamp(mem.get("timestamp", 0)).strftime("%B %d, %Y")
                
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    if mem.get("source_image_base64"):
                        st.image(base64.b64decode(mem["source_image_base64"]), width="stretch")
                    else:
                        st.markdown("🎉")
                
                with col2:
                    st.markdown(f"**{timestamp}**")
                    content = mem.get("caption") or mem.get("transcript") or mem.get("content")
                    st.write(content)
                
                st.markdown("---")
        else:
            st.info("No milestones recorded yet. Request caretaker to add achievements!")

# === TAB 2: FAMILY RECAP ===
with tab2:
    st.header("📖 Weekly & Monthly Recaps")
    st.caption("AI-generated family-friendly summaries of recent memories")
    
    recap_period = st.radio("Period", ["week", "month"], horizontal=True, key="recap_period")
    
    if st.button(f"✨ Generate {recap_period.title()} Recap", key="generate_recap"):
        with st.spinner(f"Creating your {recap_period} recap..."):
            try:
                from lifelens.agents import generate_family_summary
                summary_data = generate_family_summary(patient_id, client, period=recap_period)
                
                # Store in session state for persistence
                st.session_state.last_recap = summary_data
                
            except Exception as e:
                st.error(f"Failed to generate recap: {e}")
    
    # Display recap if it exists
    if hasattr(st.session_state, 'last_recap') and st.session_state.last_recap:
        recap = st.session_state.last_recap
        
        # Main narrative summary
        st.markdown("### 💝 Family Update")
        st.markdown(recap.get("summary", "No summary available"))
        
        st.markdown("---")
        
        # Emotional timeline
        if recap.get("emotional_timeline"):
            st.markdown("### 😊 Emotional Moments")
            for moment in recap["emotional_timeline"]:
                mood_emoji = {
                    "joyful": "😊",
                    "happy": "😄",
                    "peaceful": "😌",
                    "excited": "🤩",
                    "grateful": "🙏",
                    "sad": "😢",
                    "worried": "😟"
                }
                emoji = mood_emoji.get(moment.get("mood", "").lower(), "💭")
                st.markdown(f"{emoji} **{moment.get('date')}**: {moment.get('moment')}")
        
        st.markdown("---")
        
        # Highlights
        if recap.get("highlights"):
            st.markdown("### ⭐ Highlights")
            for highlight in recap["highlights"]:
                with st.expander(f"✨ {highlight.get('title')}", expanded=False):
                    st.write(highlight.get('description'))
                    type_icon = {
                        "image": "📸",
                        "video": "📹",
                        "audio": "🎤",
                        "text": "📝"
                    }
                    st.caption(f"{type_icon.get(highlight.get('type'), '💭')} {highlight.get('type', 'memory').title()}")
        
        st.markdown("---")
        
        # Milestones
        if recap.get("milestones"):
            st.markdown("### 🎉 Milestones")
            for milestone in recap["milestones"]:
                st.markdown(f"🎊 **{milestone.get('date')}**: {milestone.get('content')}")
        
        st.markdown("---")
        
        # Visitor recap
        if recap.get("visitor_recap"):
            st.markdown("### 👥 Visitor Activity")
            st.info(recap["visitor_recap"])
        
        st.markdown("---")
        
        # Media gallery
        if recap.get("media_gallery"):
            st.markdown("### 📸 Photo Gallery")
            st.caption(f"{len(recap['media_gallery'])} photos from this period")
            
            # Display images in grid
            cols = st.columns(4)
            try:
                for idx, memory_id in enumerate(recap["media_gallery"][:12]):
                    # Retrieve the image from Qdrant
                    try:
                        result = client.retrieve(
                            collection_name=QDRANT_COLLECTION_NAME,
                            ids=[memory_id]
                        )
                        if result and len(result) > 0:
                            payload = result[0].payload
                            if payload.get("source_image_base64"):
                                with cols[idx % 4]:
                                    st.image(base64.b64decode(payload["source_image_base64"]), width="stretch")
                                    if payload.get("caption"):
                                        st.caption(payload["caption"][:80])
                    except:
                        pass
            except Exception as e:
                st.warning(f"Could not load some images: {e}")
    else:
        st.info("👆 Click 'Generate Recap' to see your family summary")

# === TAB 3: MILESTONES ===
with tab3:
    st.header("🎉 Milestones & Achievements")
    st.caption("Track important moments and achievements")
    
    # Filter memories by type or tags
    if stats and stats["memories"]:
        # Look for achievement-related keywords or explicit categories
        achievements = []
        milestone_keywords = [
            "achievement", "milestone", "award", "celebration", "birthday", 
            "anniversary", "graduation", "wedding", "born", "birth", "win", 
            "won", "prize", "first", "success", "party", "hospital", "doctor"
        ]
        milestone_categories = ["Achievement", "Event", "Milestone", "Family Gathering"]
        
        for mem in stats["memories"]:
            # Check explicit category first
            category = mem.get("category")
            if category in milestone_categories:
                achievements.append(mem)
                continue
                
            # Fallback to keyword search
            content = (mem.get("caption") or mem.get("transcript") or mem.get("content") or "").lower()
            if any(word in content for word in milestone_keywords):
                achievements.append(mem)
        
        if achievements:
            st.write(f"**{len(achievements)} milestones found:**")
            
            for mem in sorted(achievements, key=lambda x: x.get('timestamp', 0), reverse=True):
                timestamp = datetime.fromtimestamp(mem.get("timestamp", 0)).strftime("%B %d, %Y")
                
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    if mem.get("source_image_base64"):
                        st.image(base64.b64decode(mem["source_image_base64"]), width="stretch")
                    else:
                        st.markdown("🎉")
                
                with col2:
                    st.markdown(f"**{timestamp}**")
                    content = mem.get("caption") or mem.get("transcript") or mem.get("content")
                    st.write(content)
                
                st.markdown("---")
        else:
            st.info("No milestones recorded yet. Request caretaker to add achievements!")

# === TAB 4: MEDICATIONS ===
with tab4:
    st.header("💊 Medication Tracking")
    st.caption("View medications allotted by caretaker and adherence status")
    
    from lifelens.utils.medication_utils import get_all_patient_medications
    from lifelens.agents.medication_scheduler import get_todays_medications
    from lifelens.utils.medication_utils import format_time_for_display
    
    # Get all active medications
    medications = get_all_patient_medications(client, patient_id, active_only=True)
    
    if medications:
        st.subheader("Active Medications")
        st.write(f"**{len(medications)} medications prescribed by caretaker:**")
        
        for med in medications:
            with st.expander(f"💊 {med['name']} - {med['dosage']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Dosage:** {med['dosage']}")
                    st.markdown(f"**Frequency:** {med.get('frequency', 'Not specified')}")
                    
                    if med.get('schedule'):
                        times = ", ".join([format_time_for_display(t) for t in med['schedule']])
                        st.markdown(f"**Schedule:** {times}")
                    
                    if med.get('notes'):
                        st.markdown(f"**Instructions:** {med['notes']}")
                    
                    if med.get('prescribed_by'):
                        st.caption(f"Prescribed by: {med['prescribed_by']}")
                    
                    start_date = datetime.fromisoformat(med.get('start_date', '')).strftime("%B %d, %Y") if med.get('start_date') else "Unknown"
                    st.caption(f"Started: {start_date}")
                
                with col2:
                    # Show status indicator
                    if med.get('active', True):
                        st.success("✅ Active")
                    else:
                        st.error("❌ Inactive")
        
        st.markdown("---")
        
        # Show today's schedule and completion status
        st.subheader("Today's Medication Schedule")
        
        todays_meds = get_todays_medications(client, patient_id)
        
        if todays_meds:
            # Group by status
            taken_meds = [m for m in todays_meds if m["status"] == "taken"]
            skipped_meds = [m for m in todays_meds if m["status"] == "skipped"]
            pending_meds = [m for m in todays_meds if m["status"] == "pending"]
            
            # Show metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Taken", len(taken_meds))
            with col2:
                st.metric("⏭️ Skipped", len(skipped_meds))
            with col3:
                st.metric("⏰ Pending", len(pending_meds))
            
            st.markdown("---")
            
            # Show detailed schedule
            if taken_meds:
                with st.expander(f"✅ Doses Taken ({len(taken_meds)})", expanded=True):
                    for med in taken_meds:
                        st.markdown(f"- ✅ **{med['medication_name']}** {med['dosage']} at {format_time_for_display(med['scheduled_time'])}")
            
            if pending_meds:
                with st.expander(f"⏰ Pending Doses ({len(pending_meds)})", expanded=len(taken_meds) == 0):
                    for med in pending_meds:
                        overdue_indicator = " 🔴 OVERDUE" if med.get('is_overdue') else ""
                        st.markdown(f"- ⏰ **{med['medication_name']}** {med['dosage']} at {format_time_for_display(med['scheduled_time'])}{overdue_indicator}")
            
            if skipped_meds:
                with st.expander(f"⏭️ Skipped Doses ({len(skipped_meds)})"):
                    for med in skipped_meds:
                        st.markdown(f"- ⏭️ **{med['medication_name']}** {med['dosage']} at {format_time_for_display(med['scheduled_time'])}")
        else:
            st.info("No medications scheduled for today.")
        
        st.markdown("---")
        
        # Show adherence tracking (calculate in real-time)
        st.subheader("7-Day Adherence Summary")
        
        from lifelens.utils.medication_utils import calculate_adherence_rate, get_medication_history
        from datetime import datetime, timedelta
        
        try:
            # Get medication history for last 7 days
            history = get_medication_history(client, patient_id, medication_id=None, days=7)
            
            if history:
                # Calculate metrics
                total_doses = len(history)
                taken_count = len([e for e in history if e.get("status") == "taken"])
                missed_count = len([e for e in history if e.get("status") == "missed"])
                skipped_count = len([e for e in history if e.get("status") == "skipped"])
                
                # Calculate adherence rate
                adherence_rate = calculate_adherence_rate(client, patient_id, days=7)
                adherence_pct = adherence_rate * 100
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    rate_color = "🟢" if adherence_pct >= 80 else "🟡" if adherence_pct >= 60 else "🔴"
                    st.metric(f"{rate_color} Adherence Rate", f"{adherence_pct:.1f}%")
                
                with col2:
                    st.metric("✅ Doses Taken", f"{taken_count}/{total_doses}")
                
                with col3:
                    st.metric("❌ Missed Doses", missed_count)
                
                with col4:
                    st.metric("⏭️ Skipped Doses", skipped_count)
                
                # Adherence summary message
                if adherence_pct >= 90:
                    st.success("🎉 Excellent adherence! Patient is taking medications as prescribed.")
                elif adherence_pct >= 75:
                    st.info("👍 Good adherence. Minor improvements possible.")
                elif adherence_pct >= 60:
                    st.warning("⚠️ Fair adherence. Consider discussing barriers with patient.")
                else:
                    st.error("🚨 Poor adherence. Immediate intervention may be needed.")
                
                # Show recent events
                with st.expander("📋 Recent Medication Events"):
                    for event in history[:10]:  # Show latest 10
                        status_icon = "✅" if event["status"] == "taken" else "❌" if event["status"] == "missed" else "⏭️"
                        timestamp = datetime.fromtimestamp(event.get("timestamp", 0)).strftime("%b %d, %I:%M %p")
                        med_name = event.get("medication_id", "Unknown")[:20]
                        st.caption(f"{status_icon} {med_name} - {event['status'].title()} on {timestamp}")
            else:
                st.info("No medication history available for the past 7 days.")
        except Exception as e:
            st.warning(f"Unable to calculate adherence: {e}")
            logger.error(f"Adherence calculation error: {e}", exc_info=True)
    else:
        st.info("No medications currently prescribed. Caretaker can add medications from their dashboard.")

# === TAB 5: MEMORY REQUESTS ===
with tab5:
    st.header("📝 Request Memory Addition")
    st.info("💡 Family members can request memories to be added. Caretakers will review and add them.")
    
    # Create new request
    with st.expander("➕ Create New Memory Request", expanded=True):
        st.subheader("Request a Memory")
        
        memory_type = st.selectbox(
            "Type of Memory",
            ["Achievement", "Event", "Milestone", "Family Gathering", "Other"]
        )
        
        description = st.text_area(
            "Description",
            placeholder="e.g., John's graduation ceremony on May 15th, 2024. He received honors in Computer Science.",
            help="Provide detailed description of the memory to be added"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            people_involved = st.text_input("People Involved", placeholder="e.g., John, Sarah, Mom")
        
        with col2:
            event_date = st.date_input("Event Date (if known)")
        
        location_name = st.text_input("Location (if known)", placeholder="e.g., University Auditorium")
        
        if st.button("Submit Request", type="primary"):
            if description:
                details = {
                    "people_involved": people_involved,
                    "event_date": str(event_date) if event_date else None,
                    "location": location_name
                }
                
                request_id = create_request(
                    patient_id=patient_id,
                    requester_name=user["full_name"],
                    memory_type=memory_type,
                    description=description,
                    details=details
                )
                
                st.success(f"✅ Request submitted! Request ID: {request_id}")
                st.info("A caretaker will review and add this memory soon.")
            else:
                st.warning("Please provide a description.")
    
    st.markdown("---")
    
    # View existing requests
    st.subheader("Your Requests")
    
    requests = get_requests_for_patient(patient_id)
    
    if requests:
        for req in sorted(requests, key=lambda x: x["created_at"], reverse=True):
            status_colors = {
                "pending": "🟡",
                "approved": "🟢",
                "completed": "✅",
                "rejected": "🔴"
            }
            
            icon = status_colors.get(req["status"], "⚪")
            
            with st.expander(f"{icon} {req['memory_type']} - {req['status'].upper()}"):
                st.write(f"**Requested by:** {req['requester_name']}")
                st.write(f"**Date:** {datetime.fromisoformat(req['created_at']).strftime('%B %d, %Y')}")
                st.write(f"**Description:** {req['description']}")
                
                if req.get("details"):
                    details = req["details"]
                    if details.get("people_involved"):
                        st.caption(f"👤 People: {details['people_involved']}")
                    if details.get("location"):
                        st.caption(f"📍 Location: {details['location']}")
                
                if req.get("notes"):
                    st.info(f"📝 Notes: {req['notes']}")
    else:
        st.info("No requests yet. Create your first memory request above!")

# === TAB 6: MEDIA GALLERY ===
with tab6:
    st.header("📸 Media Gallery")
    st.caption("Browse all photos and videos")
    
    if stats and stats["memories"]:
        # Filter images and videos
        images = [m for m in stats["memories"] if m.get("type") == "image" and m.get("source_image_base64")]
        videos = [m for m in stats["memories"] if m.get("type") == "video"]
        
        if images or videos:
            st.write(f"**{len(images)} photos, {len(videos)} videos**")
            
            # Display in grid
            cols = st.columns(3)
            all_media = images + videos
            
            for idx, media in enumerate(all_media):
                with cols[idx % 3]:
                    if media.get("type") == "image":
                        st.image(base64.b64decode(media["source_image_base64"]))
                        if media.get("caption"):
                            with st.expander("View Caption"):
                                st.write(media["caption"])
                    elif media.get("type") == "video":
                        if media.get("video_path") and os.path.exists(media["video_path"]):
                            st.video(media["video_path"])
                        else:
                            st.markdown("📹 **Video**")
                            st.caption("Video file not available")
                        if media.get("analysis"):
                            with st.expander("View Analysis"):
                                st.write(media["analysis"])
                    
                    timestamp = datetime.fromtimestamp(media.get("timestamp", 0)).strftime("%b %d, %Y")
                    st.caption(timestamp)
                    
                    if media.get("person_tags"):
                        st.caption(f"👤 {media['person_tags']}")
        else:
            st.info("No media available yet.")
    else:
        st.info("No memories found.")

st.markdown("---")
st.caption("👨‍👩‍👧‍👦 Family Portal - View Only Access | Contact caretaker to add or edit memories")
