import streamlit as st
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Auth
from lifelens.auth.users import authenticate, initialize_default_users, get_all_patients
from lifelens.auth.session import (
    init_session, login, logout, is_logged_in, 
    get_current_user, get_active_patient_id, set_active_patient, has_dashboard_access
)

# Setup Page Config
st.set_page_config(
    page_title="LifeLens",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session
init_session()

# Initialize default users if none exist
initialize_default_users()

# Apply Senior Mode Styles
from lifelens.utils.styles import apply_styles
apply_styles()

# LOGIN SCREEN
if not is_logged_in():
    st.title("🧠 LifeLens")
    st.markdown("### Multimodal Memory Companion")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            st.subheader("Login")
            
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login", use_container_width=True):
                user_data = authenticate(username, password)
                if user_data:
                    login(user_data)
                    st.success(f"Welcome, {user_data['full_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with register_tab:
            st.subheader("Create Account")
            
            from lifelens.auth.users import create_user, get_all_patients
            
            reg_username = st.text_input("Username", key="reg_user")
            reg_password = st.text_input("Password", type="password", key="reg_pass")
            reg_full_name = st.text_input("Full Name", key="reg_name")
            reg_role = st.selectbox("Role", ["patient", "caretaker", "family"])
            
            # If caretaker/family, select patient
            reg_patient_id = None
            if reg_role in ["caretaker", "family"]:
                patients = get_all_patients()
                if patients:
                    patient_options = {f"{p['full_name']} ({p['patient_id']})": p['patient_id'] for p in patients}
                    selected = st.selectbox("Select Patient", list(patient_options.keys()))
                    reg_patient_id = patient_options[selected]
                else:
                    st.warning("No patients found. Create a patient account first.")
            
            if st.button("Register", use_container_width=True):
                if reg_username and reg_password and reg_full_name:
                    success, message = create_user(reg_username, reg_password, reg_role, reg_full_name, reg_patient_id)
                    if success:
                        st.success(message + " Please login.")
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields.")
        
        st.markdown("---")
        st.info("""
        **Default Accounts:**
        - Patient: `patient1` / `patient123`
        - Caretaker: `caretaker1` / `care123`
        - Family: `family1` / `family123`
        """)
    
    st.stop()

# USER IS LOGGED IN
user = get_current_user()

# Role-based access control
if user["role"] != "patient":
    st.error("⛔ Access Denied")
    st.warning("This page is for **Patients only**.")
    
    if user["role"] == "caretaker":
        st.info("👉 Caretakers: Please use the **'dashboard'** page from the sidebar.")
    elif user["role"] == "family":
        st.info("👉 Family members: Please use the **'family_portal'** page from the sidebar.")
    
    st.stop()

# Import Modules (after login)
from lifelens.config import QDRANT_COLLECTION_NAME
from lifelens.qdrant.client import get_qdrant_client
from lifelens.qdrant.schema import create_collection_if_not_exists
from lifelens.ingestion.image_processor import process_image
from lifelens.ingestion.audio_processor import process_audio
from lifelens.ingestion.text_processor import process_text
from lifelens.ingestion.upsert_memory import upsert_memory
from lifelens.retrieval.search_engine import search_memories
from lifelens.retrieval.time_parser import parse_time_filter
from lifelens.retrieval.reasoning import get_answer
from lifelens.utils.display import display_memory
from lifelens.utils.logging import setup_logging

# Initialize Logging and DB
setup_logging()

try:
    client = get_qdrant_client()
    create_collection_if_not_exists(client)
except Exception as e:
    st.error(f"Failed to connect to Qdrant: {e}")
    st.stop()

# PATIENT SELECTOR (for caretaker/family)
if user["role"] in ["caretaker", "family"] and not get_active_patient_id():
    st.title("Select Patient")
    patients = get_all_patients()
    
    if patients:
        for patient in patients:
            if st.button(f"👤 {patient['full_name']} ({patient['patient_id']})", use_container_width=True):
                set_active_patient(patient['patient_id'])
                st.rerun()
    else:
        st.warning("No patients found in the system.")
    
    st.stop()

# Sidebar
st.sidebar.title(f"LifeLens 🧠")
st.sidebar.markdown(f"**{user['full_name']}** ({user['role'].title()})")
st.sidebar.markdown(f"*Patient: {get_active_patient_id()}*")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 Logout"):
    logout()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("Upload your memories to recall them later.")

# Reminders Section
from lifelens.utils.reminders import load_reminders
reminders = load_reminders()
if reminders:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔔 Reminders")
    for r in reminders:
        st.sidebar.warning(f"**{r.get('task')}**\n\n*{r.get('time')}*")

# AI Prompts Section
from lifelens.utils.ai_prompts import generate_ai_prompts
try:
    # Get recent memories for prompts
    recent_results = client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=10,
        with_payload=True,
        with_vectors=False,
        scroll_filter={"must": [{"key": "patient_id", "match": {"value": active_patient_id}}]}
    )[0]
    
    recent_memories = [p.payload for p in recent_results]
    last_upload = max([m.get("timestamp", 0) for m in recent_memories]) if recent_memories else None
    
    ai_prompts = generate_ai_prompts(recent_memories, last_upload)
    
    if ai_prompts:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🤖 AI Suggestions")
        for prompt in ai_prompts[:2]:  # Show top 2
            st.sidebar.info(prompt["message"])
except:
    pass

# Main Application Tabs
tab1, tab2, tab3 = st.tabs(["Remember This 📥", "Ask LifeLens 💬", "Memory Lane 🕰️"])

# Get active patient ID for filtering
active_patient_id = get_active_patient_id()

# --- TAB 1: MEMORY INGESTION ---
with tab1:
    st.header("Store a New Memory")
    
    ingest_type = st.radio("Memory Type", ["Image", "Audio", "Text"], horizontal=True)
    
    if ingest_type == "Image":
        uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
        camera_file = st.camera_input("Take a Photo")
        
        image_input = uploaded_file or camera_file
        
        if image_input:
            st.image(image_input, caption="Preview", width=300)
            
            # Person Tagging Input
            person_tags = st.text_input(
                "👤 Tag people in this photo (optional)",
                placeholder="e.g., Brother John, Sarah",
                help="Enter names or relationships of people in the photo"
            )
            
            # Location Input
            with st.expander("🗺️ Add Location (optional)"):
                from lifelens.utils.geocoding import search_location
                
                location_query = st.text_input(
                    "Search for a location",
                    placeholder="e.g., Eiffel Tower, Paris or New York City",
                    key="img_loc_search"
                )
                
                if st.button("Search Location", key="img_search_btn"):
                    if location_query:
                        with st.spinner("Searching..."):
                            result = search_location(location_query)
                            if result:
                                st.session_state.img_location = result
                                st.success(f"✅ Found: {result['display_name']}")
                            else:
                                st.error("Location not found. Try a different search.")
                    else:
                        st.warning("Please enter a location to search.")
                
                # Show selected location
                if 'img_location' in st.session_state and st.session_state.img_location:
                    loc = st.session_state.img_location
                    st.info(f"📍 Selected: {loc['display_name']}")
                    if st.button("Clear Location", key="img_clear_btn"):
                        st.session_state.img_location = None
                        st.rerun()
            
            # Milestone Toggle
            is_milestone = st.checkbox("🎉 Mark as a Milestone / Achievement", help="Checking this will highlight the memory in the family portal milestones tab")
            
            if st.button("Save Image Memory"):
                with st.spinner("Processing image..."):
                    try:
                        data = process_image(image_input)
                        
                        # Add person tags to data
                        if person_tags:
                            data['person_tags'] = person_tags
                        
                        # Add location
                        if 'img_location' in st.session_state and st.session_state.img_location:
                            loc = st.session_state.img_location
                            data['location'] = {"lat": loc['lat'], "lon": loc['lon'], "name": loc['display_name']}
                        
                        # Add patient_id
                        data['patient_id'] = active_patient_id
                        if is_milestone:
                            data['category'] = "Achievement"
                        
                        upsert_memory(client, "image", data)
                        st.success("Image memory saved successfully!")
                    except Exception as e:
                        st.error(f"Error: {e}")

    elif ingest_type == "Audio":
        uploaded_file = st.file_uploader("Upload Audio", type=['wav', 'mp3', 'm4a'])
        audio_input = st.audio_input("Record Audio")
        
        audio_file = uploaded_file or audio_input
        
        if audio_file:
            st.audio(audio_file)
            
            # Location Input
            with st.expander("🗺️ Add Location (optional)"):
                from lifelens.utils.geocoding import search_location
                
                location_query_audio = st.text_input(
                    "Search for a location",
                    placeholder="e.g., Central Park, New York",
                    key="audio_loc_search"
                )
                
                if st.button("Search Location", key="audio_search_btn"):
                    if location_query_audio:
                        with st.spinner("Searching..."):
                            result = search_location(location_query_audio)
                            if result:
                                st.session_state.audio_location = result
                                st.success(f"✅ Found: {result['display_name']}")
                            else:
                                st.error("Location not found.")
                
                if 'audio_location' in st.session_state and st.session_state.audio_location:
                    loc = st.session_state.audio_location
                    st.info(f"📍 Selected: {loc['display_name']}")
                    if st.button("Clear Location", key="audio_clear_btn"):
                        st.session_state.audio_location = None
                        st.rerun()
            
            # Milestone Toggle
            is_milestone_audio = st.checkbox("🎉 Mark as a Milestone / Achievement", key="ms_audio", help="Checking this will highlight the memory in the family portal milestones tab")
            
            if st.button("Save Audio Memory"):
                with st.spinner("Transcribing and saving..."):
                    try:
                        data = process_audio(audio_file)
                        st.info(f"Transcript: {data['transcript']}")
                        
                        # Add location
                        if 'audio_location' in st.session_state and st.session_state.audio_location:
                            loc = st.session_state.audio_location
                            data['location'] = {"lat": loc['lat'], "lon": loc['lon'], "name": loc['display_name']}
                        
                        # Add patient_id
                        data['patient_id'] = active_patient_id
                        if is_milestone_audio:
                            data['category'] = "Achievement"
                        
                        upsert_memory(client, "audio", data)
                        st.success("Audio memory saved successfully!")
                    except Exception as e:
                        st.error(f"Error: {e}")

    elif ingest_type == "Text":
        text_content = st.text_area("Write a Note")
        
        # Location Input
        with st.expander("🗺️ Add Location (optional)"):
            from lifelens.utils.geocoding import search_location
            
            location_query_text = st.text_input(
                "Search for a location",
                placeholder="e.g., Times Square, New York",
                key="text_loc_search"
            )
            
            if st.button("Search Location", key="text_search_btn"):
                if location_query_text:
                    with st.spinner("Searching..."):
                        result = search_location(location_query_text)
                        if result:
                            st.session_state.text_location = result
                            st.success(f"✅ Found: {result['display_name']}")
                        else:
                            st.error("Location not found.")
            
            if 'text_location' in st.session_state and st.session_state.text_location:
                loc = st.session_state.text_location
                st.info(f"📍 Selected: {loc['display_name']}")
                if st.button("Clear Location", key="text_clear_btn"):
                    st.session_state.text_location = None
                    st.rerun()
        
        # Milestone Toggle
        is_milestone_text = st.checkbox("🎉 Mark as a Milestone / Achievement", key="ms_text", help="Checking this will highlight the memory in the family portal milestones tab")
        
        if st.button("Save Note"):
            if text_content:
                with st.spinner("Saving note..."):
                    try:
                        data = process_text(text_content)
                        # Check for Reminder
                        from lifelens.utils.reminders import extract_reminder, save_reminder
                        reminder = extract_reminder(data['content'])
                        if reminder:
                            save_reminder(reminder)
                            st.toast(f"🔔 Reminder set: {reminder['task']}")
                        
                        # Add location
                        if 'text_location' in st.session_state and st.session_state.text_location:
                            loc = st.session_state.text_location
                            data['location'] = {"lat": loc['lat'], "lon": loc['lon'], "name": loc['display_name']}
                        
                        # Add patient_id
                        data['patient_id'] = active_patient_id
                        if is_milestone_text:
                            data['category'] = "Achievement"
                        
                        upsert_memory(client, "text", data)
                        st.success("Note saved successfully!")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please write something first.")

# --- TAB 2: RETRIEVAL & REASONING ---
with tab2:
    st.header("Ask LifeLens")
    
    # Voice Command Input
    st.markdown("**🎤 Voice Command** (optional)")
    voice_file = st.audio_input("Speak your question")
    
    if voice_file:
        with st.spinner("Listening..."):
            from lifelens.utils.voice_commands import process_voice_command
            voice_query = process_voice_command(voice_file)
            if voice_query:
                st.success(f"You said: *{voice_query}*")
                st.session_state.voice_query = voice_query
    
    # Smart Search Filters
    with st.expander("🔍 Advanced Filters"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_type = st.multiselect("Memory Type", ["image", "audio", "text"])
        
        with col2:
            filter_mood = st.multiselect("Mood", ["Happy", "Sad", "Angry", "Confused", "Neutral"])
        
        with col3:
            date_range = st.date_input("Date Range", [])
    
    # Text or Voice Query
    query = st.chat_input("Ask about your memories...")
    
    # Use voice query if available
    if not query and st.session_state.get("voice_query"):
        query = st.session_state.voice_query
        st.session_state.voice_query = None
    
    if query:
        st.chat_message("user").write(query)
        
        with st.spinner("Thinking..."):
            # 1. Parse Time Filters
            time_filters = parse_time_filter(query)
            
            # 2. Retrieve Memories (filtered by patient_id)
            memories = search_memories(client, query, filters=time_filters, patient_id=active_patient_id)
            
            # 3. Generate Answer
            answer = get_answer(query, memories)
            
            st.chat_message("assistant").write(answer)

            # TTS Playback
            from lifelens.utils.tts import text_to_speech
            try:
                with st.spinner("Speaking..."):
                    audio_bytes = text_to_speech(answer)
                    if audio_bytes:
                        st.audio(audio_bytes, format='audio/mp3', start_time=0)
            except Exception:
                pass
            
            # 4. Show Evidence
            with st.expander("View Retrieved Memories (Evidence)"):
                if memories:
                    for mem in memories:
                        display_memory(mem)
                        
                        # Show related memories
                        from lifelens.utils.memory_graph import find_related_memories
                        
                        # Fetch all memories for relationship detection
                        all_results = client.scroll(
                            collection_name=QDRANT_COLLECTION_NAME,
                            limit=100,
                            with_payload=True,
                            with_vectors=False,
                            scroll_filter={"must": [{"key": "patient_id", "match": {"value": active_patient_id}}]}
                        )[0]
                        all_memories = [p.payload for p in all_results]
                        
                        related = find_related_memories(all_memories, mem)
                        
                        if related:
                            st.markdown("**🔗 Related Memories:**")
                            for rel in related[:3]:  # Show top 3
                                st.caption(f"• {rel['reason']}")
                else:
                    st.write("No relevant memories found.")

# --- TAB 3: MEMORY LANE ---
with tab3:
    st.header("Memory Lane")
    st.write("Recent memories stored in LifeLens.")
    
    if st.button("Refresh Timeline"):
        results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=20,
            with_payload=True,
            with_vectors=False,
            scroll_filter={"must": [{"key": "patient_id", "match": {"value": active_patient_id}}]}
        )[0]
        
        # Sort by timestamp descending
        sorted_points = sorted(
            results, 
            key=lambda x: x.payload.get('timestamp', 0), 
            reverse=True
        )
        
        for point in sorted_points:
            mem_dict = point.payload
            display_memory(mem_dict)
