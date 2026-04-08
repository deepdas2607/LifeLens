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
from qdrant_client.http import models
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
            if st.button(f"👤 {patient['full_name']} ({patient['patient_id']})", width="stretch"):
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

# === UPLOAD MEMORY SECTION ===
st.header("📥 Upload Memory")
st.caption("Add new memories for the patient")

with st.expander("➕ Add New Memory", expanded=False):
    upload_type = st.radio("Memory Type", ["Image", "Audio", "Text"], horizontal=True, key="dashboard_upload_type")
    
    if upload_type == "Image":
        uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key="dashboard_img_upload")
        
        if uploaded_file:
            st.image(uploaded_file, caption="Preview", width=300)
            
            # Person Tagging Input
            person_tags = st.text_input(
                "👤 Tag people in this photo (optional)",
                placeholder="e.g., Brother John, Sarah",
                key="dashboard_person_tags"
            )
            
            if st.button("💾 Save Memory", key="dashboard_save_img"):
                with st.spinner("Processing..."):
                    try:
                        from lifelens.ingestion.image_processor import process_image
                        result = process_image(uploaded_file)
                        
                        data = {
                            "patient_id": patient_id,
                            "image_base64": result["image_base64"],
                            "caption": result["caption"],
                            "sentiment": result.get("sentiment")
                        }
                        
                        if person_tags:
                            data["person_tags"] = person_tags
                        
                        upsert_memory(client, "image", data)
                        st.success("✅ Memory saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    elif upload_type == "Audio":
        audio_file = st.file_uploader("Upload Audio", type=['mp3', 'wav', 'm4a', 'ogg'], key="dashboard_audio_upload")
        
        if audio_file:
            st.audio(audio_file)
            
            if st.button("💾 Save Audio Memory", key="dashboard_save_audio"):
                with st.spinner("Processing audio..."):
                    try:
                        from lifelens.ingestion.audio_processor import process_audio
                        result = process_audio(audio_file)
                        
                        data = {
                            "patient_id": patient_id,
                            "audio_base64": result["audio_base64"],
                            "transcript": result["transcript"]
                        }
                        
                        upsert_memory(client, "audio", data)
                        st.success("✅ Audio memory saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    elif upload_type == "Text":
        text_content = st.text_area("Write a note or memory", key="dashboard_text_content")
        
        if text_content and st.button("💾 Save Note", key="dashboard_save_text"):
            with st.spinner("Saving..."):
                try:
                    data = {
                        "patient_id": patient_id,
                        "content": text_content
                    }
                    upsert_memory(client, "text", data)
                    st.success("✅ Note saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")

# === MEDICATION MANAGEMENT SECTION ===
st.header("💊 Medication Management")

from lifelens.ui.medication_components import render_caretaker_medication_manager
render_caretaker_medication_manager(client, patient_id)

st.markdown("---")

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
# Activity Chart
st.subheader("Activity Over Time")
activity_df = get_activity_dataframe(stats["daily_counts"])

import plotly.express as px
import plotly.io as pio

# Define Custom Neon Template
pio.templates["neon"] = pio.templates["plotly_dark"]
pio.templates["neon"].layout.paper_bgcolor = "rgba(0,0,0,0)"
pio.templates["neon"].layout.plot_bgcolor = "rgba(0,0,0,0)"
pio.templates["neon"].layout.font.family = "Inter"
pio.templates["neon"].layout.font.color = "#cbd5e1"

if not activity_df.empty:
    fig = px.bar(
        activity_df, 
        x='Date', 
        y='Count',
        title="Daily Memories",
        template="neon",
        color_discrete_sequence=["#06b6d4"]
    )
    fig.update_traces(marker_line_width=0, marker_opacity=0.8, marker_cornerradius=5)
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig)
else:
    st.info("No activity data yet.")

st.markdown("---")

# === MOOD INTELLIGENCE SECTION ===
from lifelens.ui.mood_components import render_mood_insights

render_mood_insights(client, patient_id)

st.markdown("---")

# === AGENT INSIGHTS ===
st.subheader("🧠 Agent Observations")
st.caption("AI-generated insights about memory patterns")

with st.spinner("Analyzing patterns..."):
    try:
        from lifelens.agents import generate_dashboard_insights
        insights_data = generate_dashboard_insights(patient_id, client, days_back=7)
        
        # Display warnings first (high priority)
        if insights_data.get("warnings"):
            for warning in insights_data["warnings"]:
                st.warning(f"**⚠️ {warning['title']}**\n\n{warning['message']}")
        
        # Display insights
        if insights_data.get("insights"):
            for insight in insights_data["insights"]:
                st.info(f"**💡 {insight['title']}**\n\n{insight['message']}")
        
        # Display suggestions
        if insights_data.get("suggestions"):
            st.markdown("**📋 Suggestions:**")
            for suggestion in insights_data["suggestions"]:
                priority_emoji = "🔴" if suggestion.get("priority") == "high" else "🟡"
                st.markdown(f"{priority_emoji} **{suggestion['title']}**: {suggestion['message']}")
        
        # Summary
        if insights_data.get("summary"):
            st.caption(f"*{insights_data['summary']}*")
            
    except Exception as e:
        st.error(f"Agent insights unavailable: {e}")

st.markdown("---")

# === MOOD TRACKER ===
st.subheader("🎭 Mood Tracker")

if stats["mood_distribution"]:
    mood_df = pd.DataFrame([
        {"Sentiment": k, "Count": v}
        for k, v in stats["mood_distribution"].items()
    ])
    
    fig_mood = px.pie(
        mood_df, 
        values='Count', 
        names='Sentiment', 
        title="Emotional Distribution",
        template="neon",
        color_discrete_sequence=px.colors.qualitative.Bold,
        hole=0.4
    )
    fig_mood.update_traces(textposition='inside', textinfo='percent+label')
    fig_mood.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    st.plotly_chart(fig_mood)
else:
    st.info("No mood data recorded yet.")

st.markdown("---")

# === PEOPLE DIRECTORY ===
st.subheader("👥 People Directory")

people_memories = {}
for mem in stats["memories"]:
    # ONLY check manually typed person_tags field (no automatic extraction)
    person_list = []
    
    # Check person_tags field (comma-separated)
    if "person_tags" in mem and mem.get("person_tags"):
        if isinstance(mem["person_tags"], str):
            person_list.extend([tag.strip() for tag in mem["person_tags"].split(",") if tag.strip()])
        elif isinstance(mem["person_tags"], list):
            person_list.extend([str(tag).strip() for tag in mem["person_tags"] if str(tag).strip()])
    
    # Check people field (alternative name) - only if explicitly set
    if "people" in mem and mem.get("people"):
        if isinstance(mem["people"], str):
            person_list.extend([tag.strip() for tag in mem["people"].split(",") if tag.strip()])
        elif isinstance(mem["people"], list):
            person_list.extend([str(tag).strip() for tag in mem["people"] if str(tag).strip()])
    
    # Add to people_memories (only manually tagged people)
    for person in set(person_list):  # Use set to avoid duplicates
        if person:  # Just check if not empty
            if person not in people_memories:
                people_memories[person] = []
            
            # Store memory info
            memory_info = {
                "type": mem.get("type"),
                "timestamp": mem.get("timestamp"),
                "image": mem.get("source_image_base64"),
                "caption": mem.get("caption", ""),
                "content": mem.get("content", ""),
                "transcript": mem.get("transcript", ""),
                "analysis": mem.get("analysis", ""),
                "video_path": mem.get("video_path")
            }
            people_memories[person].append(memory_info)

if people_memories:
    st.write(f"**{len(people_memories)} people manually tagged in memories:**")
    
    for person in sorted(people_memories.keys()):
        with st.expander(f"👤 {person} ({len(people_memories[person])} memories)"):
            # Show up to 6 memories
            for idx, mem_info in enumerate(people_memories[person][:6]):
                mem_type = mem_info["type"]
                
                if mem_type == "image" and mem_info["image"]:
                    st.image(base64.b64decode(mem_info["image"]))
                    if mem_info["caption"]:
                        st.caption(mem_info["caption"][:100])
                elif mem_type == "video":
                    st.markdown("📹 **Video Memory**")
                    if mem_info["video_path"] and os.path.exists(mem_info["video_path"]):
                        st.video(mem_info["video_path"])
                    if mem_info["analysis"]:
                        st.caption(mem_info["analysis"][:100])
                elif mem_type == "audio":
                    st.markdown("🎤 **Audio Memory**")
                    if mem_info["transcript"]:
                        st.caption(mem_info["transcript"][:100])
                elif mem_type == "text":
                    st.markdown("📝 **Text Note**")
                    if mem_info["content"]:
                        st.caption(mem_info["content"][:100])
                
                st.markdown("---")
else:
    st.info("No people tagged yet. Tag people when uploading memories to see them here.")

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

# === DATA HYGIENE SCAN ===
st.subheader("🧹 Data Quality Check")
st.caption("Agent-powered memory maintenance")

if st.button("🔍 Run Hygiene Scan"):
    with st.spinner("Scanning memories for quality issues..."):
        try:
            from lifelens.agents import scan_for_hygiene_issues
            hygiene_results = scan_for_hygiene_issues(patient_id, client)
            
            # Display recommendations
            if hygiene_results.get("recommendations"):
                st.markdown("### 📋 Recommendations")
                for rec in hygiene_results["recommendations"]:
                    priority_color = {
                        "high": "🔴",
                        "medium": "🟡",
                        "low": "⚪"
                    }
                    icon = priority_color.get(rec["priority"], "⚪")
                    st.info(f"{icon} **{rec['category'].title()}**: {rec['message']}")
            
            # Show detailed issues in expanders
            if hygiene_results.get("duplicates"):
                with st.expander(f"🔄 Potential Duplicates ({len(hygiene_results['duplicates'])})"):
                    for dup in hygiene_results["duplicates"][:10]:
                        st.warning(f"**Similarity: {dup['similarity']:.2%}**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"Memory 1: {dup['content1']}")
                        with col2:
                            st.caption(f"Memory 2: {dup['content2']}")
                        st.markdown("---")
            
            if hygiene_results.get("low_quality"):
                with st.expander(f"⚠️ Quality Issues ({len(hygiene_results['low_quality'])})"):
                    for issue in hygiene_results["low_quality"][:10]:
                        st.write(f"**{issue['type']}**: {', '.join(issue['issues'])}")
                        st.caption(issue['preview'])
                        st.markdown("---")
            
            if hygiene_results.get("missing_metadata"):
                with st.expander(f"📋 Missing Metadata ({len(hygiene_results['missing_metadata'])})"):
                    for item in hygiene_results["missing_metadata"][:10]:
                        st.write(f"**{item['type']}**: {', '.join(item['issues'])}")
                        st.markdown("---")
            
            if not any([
                hygiene_results.get("duplicates"),
                hygiene_results.get("low_quality"),
                hygiene_results.get("missing_metadata")
            ]):
                st.success("✅ No issues found! Your memories are in great shape.")
                
        except Exception as e:
            st.error(f"Hygiene scan failed: {e}")

st.markdown("---")

# === MEMORY MANAGEMENT ===
st.subheader("🗑️ Memory Management")
st.warning("⚠️ Deletion is permanent and cannot be undone.")

# Fetch memories, excluding agent decisions
scroll_result = client.scroll(
    collection_name=QDRANT_COLLECTION_NAME,
    limit=100,
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
            elif mem_type == "video":
                preview = p.get("analysis", "No analysis")[:60]
                st.write(f"📹 **Video** - {timestamp}")
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
