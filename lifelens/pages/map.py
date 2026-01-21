import streamlit as st
import os
import sys
import folium
from streamlit_folium import st_folium

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.session import init_session, is_logged_in, get_active_patient_id, get_current_user
from lifelens.qdrant.client import get_qdrant_client
from lifelens.config import QDRANT_COLLECTION_NAME
from datetime import datetime

# Page Config
st.set_page_config(page_title="Memory Map", page_icon="🗺️", layout="wide")

# Apply styles
from lifelens.utils.styles import apply_styles
apply_styles()

# Initialize session
init_session()

# Check authentication only
if not is_logged_in():
    st.error("Please log in from the main page.")
    st.stop()

user = get_current_user()
patient_id = get_active_patient_id()

# Patient selector for caretaker/family
if user["role"] in ["caretaker", "family"] and not patient_id:
    st.title("🗺️ Memory Map")
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

if not patient_id:
    st.error("No patient selected.")
    st.stop()

st.title("🗺️ Memory Map")

# Logout button in sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown(f"**Logged in as:** {user['full_name']}")
    st.caption(f"Role: {user['role'].title()}")
    st.caption(f"Patient: {patient_id}")
    
    if st.button("🚪 Logout", use_container_width=True):
        from lifelens.auth.session import logout
        logout()
        st.rerun()
    
    # Change patient button for caretaker/family
    if user["role"] in ["caretaker", "family"]:
        if st.button("🔄 Change Patient", use_container_width=True):
            from lifelens.auth.session import set_active_patient
            set_active_patient(None)
            st.rerun()

st.markdown(f"**Patient:** {patient_id}")
st.markdown("---")

# Get client
client = get_qdrant_client()

# Fetch memories with location
results = client.scroll(
    collection_name=QDRANT_COLLECTION_NAME,
    limit=1000,
    with_payload=True,
    with_vectors=False,
    scroll_filter={"must": [{"key": "patient_id", "match": {"value": patient_id}}]}
)[0]

memories_with_location = []
for point in results:
    p = point.payload
    if "location" in p and p["location"]:
        memories_with_location.append(p)

if not memories_with_location:
    st.info("No memories with location data yet. Add locations when uploading memories!")
    st.stop()

# Create map centered on first memory
first_loc = memories_with_location[0]["location"]
m = folium.Map(location=[first_loc["lat"], first_loc["lon"]], zoom_start=12)

# Add markers for each memory
for mem in memories_with_location:
    loc = mem["location"]
    
    # Create popup content
    timestamp = datetime.fromtimestamp(mem.get("timestamp", 0)).strftime("%B %d, %Y")
    
    popup_html = f"""
    <div style="width: 200px;">
        <b>{mem.get('type', 'Memory').upper()}</b><br>
        <i>{timestamp}</i><br>
    """
    
    if mem.get("caption"):
        popup_html += f"<p>{mem['caption'][:100]}...</p>"
    elif mem.get("transcript"):
        popup_html += f"<p>{mem['transcript'][:100]}...</p>"
    elif mem.get("content"):
        popup_html += f"<p>{mem['content'][:100]}...</p>"
    
    popup_html += "</div>"
    
    # Choose marker color based on type
    color_map = {
        "image": "blue",
        "audio": "green",
        "text": "orange"
    }
    color = color_map.get(mem.get("type"), "gray")
    
    folium.Marker(
        location=[loc["lat"], loc["lon"]],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{mem.get('type', 'Memory').upper()} - {timestamp}",
        icon=folium.Icon(color=color, icon="info-sign")
    ).add_to(m)

# Display map
st_folium(m, width=1200, height=600)

st.markdown("---")
st.write(f"**{len(memories_with_location)} memories with location data**")

# Legend
st.markdown("""
**Legend:**
- 🔵 Blue: Images
- 🟢 Green: Audio
- 🟠 Orange: Text
""")
