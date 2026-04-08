import streamlit as st
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.session import init_session, is_logged_in, get_current_user, get_active_patient_id
from lifelens.qdrant.client import get_qdrant_client
from lifelens.ingestion.video_processor import process_video
from lifelens.ingestion.upsert_memory import upsert_memory
from lifelens.ui.components import card, load_css
from datetime import datetime
import time

# Page Config
st.set_page_config(page_title="Wearable Simulation", page_icon="👓", layout="wide")

# Apply Styles
from lifelens.utils.styles import apply_styles
apply_styles()
load_css()

# Session
init_session()
if not is_logged_in():
    st.error("Please log in.")
    st.stop()

st.title("👓 Wearable Capture Simulation")
st.markdown("**Simulating: Meta Ray-Ban Smart Glasses**")

# Sidebar with logout
with st.sidebar:
    user = get_current_user()
    st.markdown("---")
    st.markdown("### 👤 Session Info")
    st.caption(f"User: {user['full_name']}")
    st.caption(f"Role: {user['role'].title()}")
    patient_id = get_active_patient_id()
    if patient_id:
        st.caption(f"Patient: {patient_id}")
    st.markdown("---")
    
    if st.button("🚪 Logout", type="primary"):
        from lifelens.auth.session import logout
        logout()
        st.rerun()

# Access Control - Only caretaker and patient can access wearable
if user["role"] not in ["caretaker", "patient"]:
    st.error("Access Denied. Wearable simulation is only available to Caretakers and Patients.")
    st.info("👨‍👩‍👧‍👦 Family members: Please use the Family Portal instead.")
    st.stop()

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🔴 Live Capture")
    
    # Simple JS Video Recorder Embed
    html_code = """
    <div style="border: 2px solid #06b6d4; padding: 20px; border-radius: 12px; background: rgba(0,0,0,0.3); text-align: center;">
        <h3 style="color: white;">Smart Glasses HUD</h3>
        <video id="preview" width="100%" height="auto" autoplay muted style="border-radius: 8px; margin-bottom: 10px; max-height: 400px; object-fit: cover;"></video>
        <div style="display: flex; justify-content: center; gap: 10px;">
            <button id="startBtn" style="background: #ef4444; color: white; border: none; padding: 10px 20px; border-radius: 20px; font-weight: bold; cursor: pointer;">🔴 Record</button>
            <button id="stopBtn" disabled style="background: #64748b; color: white; border: none; padding: 10px 20px; border-radius: 20px; font-weight: bold; cursor: pointer;">⬛ Stop</button>
        </div>
        <p style="color: #94a3b8; margin-top: 10px;">Status: <span id="status">Ready</span></p>
    </div>

    <script>
        let preview = document.getElementById("preview");
        let startBtn = document.getElementById("startBtn");
        let stopBtn = document.getElementById("stopBtn");
        let status = document.getElementById("status");
        let mediaRecorder;
        let chunks = [];

        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
            .then(stream => {
                preview.srcObject = stream;
                
                mediaRecorder = new MediaRecorder(stream);
                
                mediaRecorder.ondataavailable = e => chunks.push(e.data);
                
                mediaRecorder.onstop = e => {
                    let blob = new Blob(chunks, { type: "video/webm" });
                    chunks = [];
                    let url = URL.createObjectURL(blob);
                    
                    // Create download link
                    let a = document.createElement("a");
                    a.href = url;
                    a.download = "glasses_capture.webm";
                    a.click();
                    
                    status.innerText = "Saved to Downloads folder. Please Upload below to Sync.";
                    status.style.color = "#4ade80";
                };
                
                startBtn.onclick = () => {
                    mediaRecorder.start();
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    startBtn.style.background = "#64748b";
                    stopBtn.style.background = "#ef4444";
                    status.innerText = "Recording...";
                    status.style.color = "#ef4444";
                };
                
                stopBtn.onclick = () => {
                    mediaRecorder.stop();
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    startBtn.style.background = "#ef4444";
                    stopBtn.style.background = "#64748b";
                };
            })
            .catch(err => {
                console.error(err);
                status.innerText = "Camera access denied: " + err.message;
            });
    </script>
    """
    st.components.v1.html(html_code, height=600, scrolling=True)
    
    st.info("ℹ️ **Simulation Flow**: Record using the HUD above -> The file downloads -> Upload it below to 'Sync' with LifeLens.")

with col2:
    st.markdown("### ☁️ Sync to LifeLens")
    
    uploaded_video = st.file_uploader("Upload Capture", type=['mp4', 'webm', 'mov'])
    
    if uploaded_video:
        st.video(uploaded_video)
        
        # Tags and Location Inputs
        person_tags = st.text_input("👤 Tag People (Optional)", placeholder="e.g. John, Mary")
        
        # Location Input
        with st.expander("🗺️ Add Location (optional)"):
            from lifelens.utils.geocoding import search_location
            
            location_query_video = st.text_input(
                "Search for a location",
                placeholder="e.g., Central Park",
                key="video_loc_search"
            )
            
            if st.button("Search Location", key="video_search_btn"):
                if location_query_video:
                    with st.spinner("Searching..."):
                        result = search_location(location_query_video)
                        if result:
                            st.session_state.video_location = result
                            st.success(f"✅ Found: {result['display_name']}")
                        else:
                            st.error("Location not found.")
            
            if 'video_location' in st.session_state and st.session_state.video_location:
                loc = st.session_state.video_location
                st.info(f"📍 Selected: {loc['display_name']}")
                if st.button("Clear Location", key="video_clear_btn"):
                    st.session_state.video_location = None
                    st.rerun()

        patient_id = get_active_patient_id()
        if not patient_id:
            st.warning("Please select a patient in Dashboard or Family Portal first.")
        else:
            if st.button("🚀 Process & Save Memory", type="primary"):
                with st.spinner("Analyzing Scene..."):
                    try:
                        # 1. Save Video Locally (for playback)
                        # Create unique filename
                        import uuid
                        video_ext = uploaded_video.name.split('.')[-1]
                        video_filename = f"{uuid.uuid4()}.{video_ext}"
                        
                        # Use absolute path to ensure persistence/finding works
                        base_dir = os.path.dirname(os.path.abspath(__file__)) # lifelens/pages
                        project_root = os.path.dirname(os.path.dirname(base_dir)) # lifelens root? No.
                        # Actually app runs in lifelens/, so os.getcwd() should be lifelens/
                        # Let's rely on os.getcwd() but make it absolute
                        
                        video_dir = os.path.join(os.getcwd(), "static", "videos")
                        os.makedirs(video_dir, exist_ok=True)
                        save_path = os.path.join(video_dir, video_filename)
                        
                        # Write buffer to file
                        with open(save_path, "wb") as f:
                            f.write(uploaded_video.getbuffer())
                            
                        # 2. Process with Gemini
                        # We can pass the saved file path if needed, or the uploaded_video object
                        uploaded_video.seek(0) # Reset pointer
                        result = process_video(uploaded_video)
                        
                        # Display Analysis
                        st.success("Analysis Complete!")
                        st.markdown(result["analysis"])
                        
                        # 3. Save to Qdrant
                        client = get_qdrant_client()
                        data = {
                            "analysis": result["analysis"],
                            "patient_id": patient_id,
                            "category": "Wearable Capture",
                            "video_path": save_path  # Store the local path
                        }
                        
                        # Add metadata
                        if person_tags:
                            data['person_tags'] = person_tags
                        
                        if 'video_location' in st.session_state and st.session_state.video_location:
                            loc = st.session_state.video_location
                            data['location'] = {"lat": loc['lat'], "lon": loc['lon'], "name": loc['display_name']}

                        upsert_memory(client, "video", data)
                        
                        st.toast("Memory Saved to Qdrant!", icon="🧠")
                        time.sleep(2) # Give it a moment before reload
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error: {e}")

st.markdown("---")
st.markdown("### 🧠 Recent Captures")

# Fetch recent video memories
from lifelens.config import QDRANT_COLLECTION_NAME
import base64

try:
    client = get_qdrant_client()
    from qdrant_client.http import models
    
    # Scroll for video type memories
    video_results = client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=10,
        with_payload=True,
        with_vectors=False,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="patient_id",
                    match=models.MatchValue(value=get_active_patient_id())
                ),
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value="video")
                )
            ]
        )
    )[0]
    
    if video_results:
        # Sort by timestamp descending
        video_results.sort(key=lambda x: x.payload.get('timestamp', 0), reverse=True)
        
        for point in video_results:
            mem = point.payload
            
            with st.expander(f"📹 Capture - {datetime.fromtimestamp(mem.get('timestamp', 0)).strftime('%I:%M %p, %b %d')}"):
                col_a, col_b = st.columns([1, 2])
                
                with col_a:
                    st.info("Video File")
                    if mem.get('video_path') and os.path.exists(mem['video_path']):
                        st.video(mem['video_path'])
                    else:
                         st.warning("Video file missing.")
                    st.caption("Video content processed.")
                
                with col_b:
                    st.markdown(mem.get('analysis', 'No analysis available.'))
    else:
        st.info("No recent video captures found.")

except Exception as e:
    st.error(f"Could not load recent captures: {type(e).__name__} - {e}")
