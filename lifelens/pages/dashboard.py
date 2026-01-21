import streamlit as st
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.session import init_session, is_logged_in, get_current_user, get_active_patient_id, has_dashboard_access
from lifelens.qdrant.client import get_qdrant_client
from lifelens.ingestion.image_processor import process_image
from lifelens.ingestion.upsert_memory import upsert_memory
from lifelens.config import QDRANT_COLLECTION_NAME
from lifelens.utils.analytics import get_memory_stats, get_activity_dataframe
from lifelens.utils.export import generate_memory_book_html
import pandas as pd
import altair as alt
from datetime import datetime
import base64

# Page Config
st.set_page_config(page_title="Caregiver Dashboard", page_icon="🛡️", layout="wide")

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

# Check dashboard access (Caretakers only)
if user["role"] != "caretaker":
    st.error("Access Denied. Only Caretakers can access this dashboard.")
    st.info("👨‍👩‍👧‍👦 Family members: Please use the 'family_portal' page instead.")
    st.stop()

patient_id = get_active_patient_id()

# Patient selector if not selected
if not patient_id:
    st.title("🛡️ Caregiver Dashboard")
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

st.title(f"🛡️ Dashboard for Patient {patient_id}")
st.markdown(f"**Logged in as:** {user['full_name']} ({user['role'].title()})")

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

# Get stats
stats = get_memory_stats(client, patient_id)

if not stats:
    st.warning("No memories found for this patient.")
    st.stop()

# === ANALYTICS SECTION ===
st.header("📊 Memory Analytics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Memories", stats["total_count"])

with col2:
    st.metric("This Week", stats["recent_count"])

with col3:
    st.metric("🔥 Streak", f"{stats['streak']} days")

with col4:
    image_count = stats["type_counts"].get("image", 0)
    st.metric("📸 Photos", image_count)

st.markdown("---")

# Activity Chart
st.subheader("Activity Over Time")
activity_df = get_activity_dataframe(stats["daily_counts"])

if not activity_df.empty:
    chart = alt.Chart(activity_df).mark_bar().encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('Count:Q', title='Memories'),
        tooltip=['Date', 'Count']
    ).properties(height=300)
    
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No activity data yet.")

st.markdown("---")

# === MOOD TRACKER ===
st.subheader("🎭 Mood Tracker")

if stats["mood_distribution"]:
    mood_df = pd.DataFrame([
        {"Sentiment": k, "Count": v}
        for k, v in stats["mood_distribution"].items()
    ])
    
    mood_chart = alt.Chart(mood_df).mark_bar().encode(
        x='Sentiment',
        y='Count',
        color='Sentiment'
    ).properties(title="Emotional Trends", height=250)
    
    st.altair_chart(mood_chart, use_container_width=True)
else:
    st.info("No mood data recorded yet.")

st.markdown("---")

# === PEOPLE DIRECTORY ===
st.subheader("👥 People Directory")

people_photos = {}
for mem in stats["memories"]:
    if "person_tags" in mem and "source_image_base64" in mem:
        tags = [tag.strip() for tag in mem["person_tags"].split(",")]
        for person in tags:
            if person not in people_photos:
                people_photos[person] = []
            people_photos[person].append({
                "image": mem["source_image_base64"],
                "caption": mem.get("caption", "No caption")[:50]
            })

if people_photos:
    st.write(f"**{len(people_photos)} people tagged:**")
    
    for person in sorted(people_photos.keys()):
        with st.expander(f"👤 {person} ({len(people_photos[person])} photos)"):
            cols = st.columns(3)
            for idx, photo in enumerate(people_photos[person][:6]):  # Limit to 6
                with cols[idx % 3]:
                    st.image(base64.b64decode(photo["image"]), use_column_width=True)
                    st.caption(photo["caption"] + "...")
else:
    st.info("No people tagged yet.")

st.markdown("---")

# === MEMORY EXPORT ===
st.subheader("📖 Export Memory Book")

if st.button("Generate Memory Book (HTML)"):
    with st.spinner("Generating memory book..."):
        html_content = generate_memory_book_html(stats["memories"], f"Patient {patient_id}")
        
        st.download_button(
            label="📥 Download Memory Book",
            data=html_content,
            file_name=f"memory_book_{patient_id}_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )
        st.success("Memory book generated! Click above to download.")

st.markdown("---")

# === MEMORY REQUESTS FROM FAMILY ===
st.subheader("📨 Memory Requests from Family")
st.caption("Review and fulfill memory requests from family members")

from lifelens.utils.memory_requests import get_requests_for_patient, update_request_status

requests = get_requests_for_patient(patient_id)

if requests:
    # Filter tabs
    req_tab1, req_tab2, req_tab3 = st.tabs(["Pending", "Completed", "All"])
    
    with req_tab1:
        pending = [r for r in requests if r["status"] == "pending"]
        if pending:
            st.write(f"**{len(pending)} pending requests**")
            
            for req in pending:
                with st.expander(f"🔔 {req['memory_type']} from {req['requester_name']}", expanded=True):
                    st.write(f"**Description:** {req['description']}")
                    
                    if req.get("details"):
                        details = req["details"]
                        if details.get("people_involved"):
                            st.caption(f"👤 People: {details['people_involved']}")
                        if details.get("event_date"):
                            st.caption(f"📅 Date: {details['event_date']}")
                        if details.get("location"):
                            st.caption(f"📍 Location: {details['location']}")
                    
                    st.markdown("---")
                    st.markdown("**Fulfill this request:**")
                    
                    # Quick fulfillment form
                    fulfill_type = st.selectbox("Add as", ["Text Note", "Upload Image"], key=f"type_{req['id']}")
                    
                    if fulfill_type == "Text Note":
                        note_content = st.text_area(
                            "Memory Content",
                            value=req['description'],
                            key=f"note_{req['id']}"
                        )
                        
                        # Location Search
                        with st.expander("🗺️ Add Location (Optional)"):
                            default_loc = req.get('details', {}).get('location', "")
                            loc_query = st.text_input("Search Location", value=default_loc, key=f"loc_query_text_{req['id']}")
                            loc_data = None
                            if st.button("Search Location", key=f"loc_btn_text_{req['id']}"):
                                from lifelens.utils.geocoding import search_location
                                loc_data = search_location(loc_query)
                                if loc_data:
                                    st.success(f"✅ Found: {loc_data['display_name']}")
                                    st.session_state[f"found_loc_text_{req['id']}"] = loc_data
                                else:
                                    st.error("Location not found.")
                            
                            # Retrieve from session state if found
                            loc_data = st.session_state.get(f"found_loc_text_{req['id']}")
                            if loc_data:
                                st.caption(f"📍 Selected: {loc_data['display_name']}")
                        
                        if st.button("✅ Add Memory & Complete Request", key=f"add_note_{req['id']}"):
                            try:
                                from lifelens.ingestion.text_processor import process_text
                                
                                data = process_text(note_content)
                                data['patient_id'] = patient_id
                                data['category'] = req['memory_type']
                                
                                # Add person tags if provided
                                if req.get('details', {}).get('people_involved'):
                                    data['person_tags'] = req['details']['people_involved']
                                
                                # Add location if found
                                if st.session_state.get(f"found_loc_text_{req['id']}"):
                                    data['location'] = st.session_state[f"found_loc_text_{req['id']}"]
                                
                                upsert_memory(client, "text", data)
                                update_request_status(req['id'], "completed", "Memory added as text note")
                                
                                # Clear session state
                                if f"found_loc_text_{req['id']}" in st.session_state:
                                    del st.session_state[f"found_loc_text_{req['id']}"]
                                
                                st.success("✅ Memory added and request completed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    
                    elif fulfill_type == "Upload Image":
                        uploaded_img = st.file_uploader(
                            "Upload photo for this memory",
                            type=['png', 'jpg', 'jpeg'],
                            key=f"img_{req['id']}"
                        )
                        
                        if uploaded_img:
                            st.image(uploaded_img, width=300)
                            
                            # Location Search
                            with st.expander("🗺️ Add Location (Optional)"):
                                default_loc = req.get('details', {}).get('location', "")
                                loc_query = st.text_input("Search Location", value=default_loc, key=f"loc_query_img_{req['id']}")
                                loc_data = None
                                if st.button("Search Location", key=f"loc_btn_img_{req['id']}"):
                                    from lifelens.utils.geocoding import search_location
                                    loc_data = search_location(loc_query)
                                    if loc_data:
                                        st.success(f"✅ Found: {loc_data['display_name']}")
                                        st.session_state[f"found_loc_img_{req['id']}"] = loc_data
                                    else:
                                        st.error("Location not found.")
                                
                                # Retrieve from session state if found
                                loc_data = st.session_state.get(f"found_loc_img_{req['id']}")
                                if loc_data:
                                    st.caption(f"📍 Selected: {loc_data['display_name']}")
                            
                            if st.button("✅ Add Photo & Complete Request", key=f"add_img_{req['id']}"):
                                try:
                                    data = process_image(uploaded_img)
                                    data['patient_id'] = patient_id
                                    data['category'] = req['memory_type']
                                    
                                    # Add person tags if provided
                                    if req.get('details', {}).get('people_involved'):
                                        data['person_tags'] = req['details']['people_involved']
                                    
                                    # Add location if found
                                    if st.session_state.get(f"found_loc_img_{req['id']}"):
                                        data['location'] = st.session_state[f"found_loc_img_{req['id']}"]
                                    
                                    upsert_memory(client, "image", data)
                                    update_request_status(req['id'], "completed", "Memory added as photo")
                                    
                                    # Clear session state
                                    if f"found_loc_img_{req['id']}" in st.session_state:
                                        del st.session_state[f"found_loc_img_{req['id']}"]
                                    
                                    st.success("✅ Photo added and request completed!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    st.markdown("---")
                    
                    # Manual status update
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔵 Mark as Approved (I'll add later)", key=f"approve_{req['id']}"):
                            update_request_status(req['id'], "approved")
                            st.info("Approved! Don't forget to add the memory.")
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ Reject Request", key=f"reject_{req['id']}"):
                            update_request_status(req['id'], "rejected")
                            st.warning("Request rejected.")
                            st.rerun()
        else:
            st.info("✅ No pending requests. All caught up!")
    
    with req_tab2:
        completed = [r for r in requests if r["status"] == "completed"]
        if completed:
            st.write(f"**{len(completed)} completed requests**")
            for req in completed:
                st.success(f"✅ {req['memory_type']} - {req['description'][:60]}...")
                if req.get('notes'):
                    st.caption(f"Note: {req['notes']}")
        else:
            st.info("No completed requests yet.")
    
    with req_tab3:
        st.write(f"**{len(requests)} total requests**")
        for req in requests:
            status_icon = {
                "pending": "🔔",
                "approved": "🔵",
                "completed": "✅",
                "rejected": "❌"
            }
            icon = status_icon.get(req["status"], "⚪")
            st.write(f"{icon} {req['memory_type']} - {req['status'].upper()} - {req['description'][:50]}...")
else:
    st.info("📨 No memory requests yet. Family members can submit requests via the Family Portal.")

st.markdown("---")

# === MEMORY MANAGEMENT ===
st.subheader("🗑️ Memory Management")
st.warning("⚠️ Deletion is permanent and cannot be undone.")

# Fetch memories
scroll_result = client.scroll(
    collection_name=QDRANT_COLLECTION_NAME,
    limit=50,
    with_payload=True,
    with_vectors=False,
    scroll_filter={"must": [{"key": "patient_id", "match": {"value": patient_id}}]}
)[0]

if scroll_result:
    st.write(f"**{len(scroll_result)} memories:**")
    
    for point in scroll_result:
        p = point.payload
        mem_type = p.get("type", "unknown")
        timestamp = datetime.fromtimestamp(p.get("timestamp", 0)).strftime("%b %d, %Y %I:%M %p")
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            if mem_type == "image":
                preview = p.get("caption", "No caption")[:60]
                st.write(f"🖼️ **Image** - {timestamp}")
                st.caption(preview)
            elif mem_type == "audio":
                preview = p.get("transcript", "No transcript")[:60]
                st.write(f"🎤 **Audio** - {timestamp}")
                st.caption(preview)
            elif mem_type == "text":
                preview = p.get("content", "No content")[:60]
                st.write(f"📝 **Text** - {timestamp}")
                st.caption(preview)
        
        with col2:
            if st.button("🗑️ Delete", key=f"del_{point.id}"):
                try:
                    client.delete(
                        collection_name=QDRANT_COLLECTION_NAME,
                        points_selector=[point.id]
                    )
                    st.success("Deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")
        
        st.markdown("---")
else:
    st.info("No memories to manage.")
