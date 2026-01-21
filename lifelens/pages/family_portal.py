import streamlit as st
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.session import init_session, is_logged_in, get_current_user, get_active_patient_id
from lifelens.qdrant.client import get_qdrant_client
from lifelens.config import QDRANT_COLLECTION_NAME
from lifelens.utils.analytics import get_memory_stats
from lifelens.utils.memory_requests import create_request, get_requests_for_patient
import pandas as pd
import altair as alt
from datetime import datetime
import base64

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
            if st.button(f"👤 {patient['full_name']} ({patient['patient_id']})", use_container_width=True):
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
    
    if st.button("🔄 Change Patient", use_container_width=True):
        from lifelens.auth.session import set_active_patient
        set_active_patient(None)
        st.rerun()
    
    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        from lifelens.auth.session import logout
        logout()
        st.rerun()

st.markdown("---")

# Get client
client = get_qdrant_client()

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🎉 Milestones", "📝 Memory Requests", "📸 Photo Gallery"])

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
        
        # Get recent memories
        recent_results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=5,
            with_payload=True,
            with_vectors=False,
            scroll_filter={"must": [{"key": "patient_id", "match": {"value": patient_id}}]}
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
                        st.image(base64.b64decode(mem["source_image_base64"]), use_column_width=True)
                    else:
                        st.markdown("🎉")
                
                with col2:
                    st.markdown(f"**{timestamp}**")
                    content = mem.get("caption") or mem.get("transcript") or mem.get("content")
                    st.write(content)
                
                st.markdown("---")
        else:
            st.info("No milestones recorded yet. Request caretaker to add achievements!")

# === TAB 3: MEMORY REQUESTS ===
with tab3:
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

# === TAB 4: PHOTO GALLERY ===
with tab4:
    st.header("📸 Photo Gallery")
    st.caption("Browse all photos in a gallery view")
    
    if stats and stats["memories"]:
        # Filter only images
        images = [m for m in stats["memories"] if m.get("type") == "image" and m.get("source_image_base64")]
        
        if images:
            st.write(f"**{len(images)} photos**")
            
            # Display in grid
            cols = st.columns(3)
            
            for idx, img in enumerate(images):
                with cols[idx % 3]:
                    st.image(base64.b64decode(img["source_image_base64"]), use_column_width=True)
                    
                    timestamp = datetime.fromtimestamp(img.get("timestamp", 0)).strftime("%b %d, %Y")
                    st.caption(timestamp)
                    
                    if img.get("person_tags"):
                        st.caption(f"👤 {img['person_tags']}")
                    
                    if img.get("caption"):
                        with st.expander("View Caption"):
                            st.write(img["caption"])
        else:
            st.info("No photos available yet.")
    else:
        st.info("No memories found.")

st.markdown("---")
st.caption("👨‍👩‍👧‍👦 Family Portal - View Only Access | Contact caretaker to add or edit memories")
