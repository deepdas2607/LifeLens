import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

import streamlit as st
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Auth
from lifelens.auth.users import authenticate, initialize_default_users, get_all_patients
from qdrant_client.http import models
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

# Apply Premium Dark Mode UI
from lifelens.ui.components import load_css
load_css()

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
            
            if st.button("Login", width="stretch"):
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
            
            if st.button("Register", width="stretch"):
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
from lifelens.qdrant.schema import create_collection_if_not_exists, create_mood_collections_if_not_exist
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
    create_mood_collections_if_not_exist(client)  # Initialize mood intelligence collections
    from lifelens.qdrant.schema import create_medication_collections_if_not_exist, create_agent_decisions_collection_if_not_exist
    create_medication_collections_if_not_exist(client)  # Initialize medication tracking collections
    create_agent_decisions_collection_if_not_exist(client)  # Initialize agent decision logging (multiagent compliance)
except Exception as e:
    st.error(f"Failed to connect to Qdrant: {e}")
    st.stop()

# PATIENT SELECTOR (for caretaker/family)
if user["role"] in ["caretaker", "family"] and not get_active_patient_id():
    st.title("Select Patient")
    patients = get_all_patients()
    
    if patients:
        for patient in patients:
            if st.button(f"👤 {patient['full_name']} ({patient['patient_id']})", width="stretch"):
                set_active_patient(patient['patient_id'])
                st.rerun()
    else:
        st.warning("No patients found in the system.")
    
    st.stop()

# Get active patient ID once for use throughout the app
active_patient_id = get_active_patient_id()

# Sidebar
st.sidebar.title(f"LifeLens 🧠")
st.sidebar.markdown(f"**{user['full_name']}** ({user['role'].title()})")
st.sidebar.markdown(f"*Patient: {get_active_patient_id()}*")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 Logout"):
    logout()
    st.rerun()

st.sidebar.markdown("---")

# Agentic Mode Toggle
from lifelens.config import AGENTIC_MODE_ENABLED
if "agentic_mode" not in st.session_state:
    st.session_state.agentic_mode = AGENTIC_MODE_ENABLED

st.sidebar.subheader("🤖 AI Mode")
agentic_toggle = st.sidebar.toggle(
    "Multi-Agent System",
    value=st.session_state.agentic_mode,
    help="Enable autonomous multi-agent decision making"
)
st.session_state.agentic_mode = agentic_toggle

if st.session_state.agentic_mode:
    st.sidebar.success("✅ Agentic Mode Active")
    st.sidebar.caption("Using: Planner → Retriever → Executor → Critic → Trigger → Recommender")
else:
    st.sidebar.info("ℹ️ Legacy Mode Active")
    st.sidebar.caption("Using: Traditional search + reasoning")

st.sidebar.markdown("---")
st.sidebar.info("Upload your memories to recall them later.")

# Medication Widget for Patients
if user["role"] == "patient":
    st.sidebar.markdown("---")
    from lifelens.ui.medication_components import render_medication_overview_widget
    try:
        render_medication_overview_widget(client, active_patient_id)
    except Exception as e:
        st.sidebar.error("Unable to load medication info")

# Reminders Section
from lifelens.utils.reminders import load_reminders
reminders = load_reminders()
if reminders:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔔 Reminders")
    for r in reminders:
        st.sidebar.warning(f"**{r.get('task')}**\n\n*{r.get('time')}*")

# AI Prompts Section (Enhanced with Recommender Agent in Agentic Mode)
if st.session_state.agentic_mode:
    # Use Recommender Agent
    try:
        from lifelens.agents import suggest_captures
        
        ai_prompts = suggest_captures(active_patient_id, client)
        
        if ai_prompts:
            st.sidebar.markdown("---")
            st.sidebar.subheader("🤖 AI Suggestions")
            st.sidebar.caption("*Powered by Recommender Agent*")
            for prompt in ai_prompts[:3]:  # Show top 3
                st.sidebar.info(prompt.get("message", "Suggestion"))
    except Exception as e:
        # Fallback to legacy prompts
        pass
else:
    # Legacy AI Prompts
    from lifelens.utils.ai_prompts import generate_ai_prompts
    try:
        # Get recent memories for prompts, excluding agent decisions
        recent_results = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=20,
            with_payload=True,
            with_vectors=False,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=active_patient_id)
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

# Trigger System Integration
from lifelens.ui.trigger_components import handle_trigger_lifecycle

handle_trigger_lifecycle(client, active_patient_id)


# Main Application Tabs
tab1, tab2, tab3 = st.tabs(["Remember This 📥", "Ask LifeLens 💬", "Memory Lane 🕰️"])

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
    
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Clear chat button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ Clear Chat", width="stretch"):
            st.session_state.chat_history = []
            st.rerun()
    
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
    
    # Smart Search Filters (kept for legacy mode fallback)
    with st.expander("🔍 Advanced Filters (Legacy Mode Only)"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_type = st.multiselect("Memory Type", ["image", "audio", "text"])
        
        with col2:
            filter_mood = st.multiselect("Mood", ["Happy", "Sad", "Angry", "Confused", "Neutral"])
        
        with col3:
            date_range = st.date_input("Date Range", [])
    
    # Display chat history
    for chat in st.session_state.chat_history:
        st.chat_message("user").write(chat["query"])
        st.chat_message("assistant", avatar="🤖").write(chat["answer"])
        
        # Display agent workflow if available (agentic mode)
        if "result" in chat:
            result = chat["result"]
            with st.expander("🔍 Agent Workflow & Analysis", expanded=False):
                agent_tab1, agent_tab2, agent_tab3, agent_tab4, agent_tab5 = st.tabs([
                    "📋 Planner", "✅ Critic", "🔔 Triggers", "💡 Recommendations", "🔍 Agent Trace"
                ])
                
                with agent_tab1:
                    st.markdown("### Planner Agent Decision")
                    st.json(result["plan"])
                    st.markdown("**Reasoning:**")
                    st.info(result["plan"].get("reasoning", "No reasoning provided"))
                    if result["plan"].get("retrieve", True):
                        st.success(f"✅ Retrieved {len(result['sources'])} memories")
                    else:
                        st.info("ℹ️ No retrieval needed (direct answer)")
                
                with agent_tab2:
                    st.markdown("### Critic Agent Evaluation")
                    verdict_emoji = {
                        "OK": "✅", "RETRY_RETRIEVAL": "🔄",
                        "SUGGEST_TRIGGER": "💡", "REQUEST_MORE_DATA": "📥"
                    }
                    verdict_desc = {
                        "OK": "Answer is well-grounded and confident",
                        "RETRY_RETRIEVAL": "Memories not relevant, retried search",
                        "SUGGEST_TRIGGER": "Answer is weak, suggest capturing more data",
                        "REQUEST_MORE_DATA": "Not enough memories to answer confidently"
                    }
                    st.markdown(f"**Verdict:** {verdict_emoji.get(result['verdict'], '❓')} {result['verdict']}")
                    st.info(verdict_desc.get(result['verdict'], "Unknown verdict"))
                    if result["retry_count"] > 0:
                        st.warning(f"🔄 Retried {result['retry_count']} time(s) to improve answer quality")
                
                with agent_tab3:
                    st.markdown("### Trigger Agent Suggestions")
                    if result["triggers"]:
                        for idx, trigger in enumerate(result["triggers"], 1):
                            priority_color = {
                                "urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"
                            }
                            priority_icon = priority_color.get(trigger.get("priority", "medium"), "🔵")
                            with st.container():
                                st.markdown(f"**{priority_icon} Trigger #{idx}**")
                                st.write(trigger.get("message", "Notification"))
                                st.caption(f"Type: {trigger.get('type', 'unknown')} | Priority: {trigger.get('priority', 'medium')}")
                                st.markdown("---")
                    else:
                        st.success("✅ No triggers needed - everything looks good!")
                
                with agent_tab4:
                    st.markdown("### Recommender Agent Suggestions")
                    if result.get("recommendations"):
                        for idx, rec in enumerate(result["recommendations"], 1):
                            st.info(f"**{idx}.** {rec.get('message', 'Suggestion')}")
                    else:
                        st.info("No specific capture recommendations at this time.")
                
                with agent_tab5:
                    st.markdown("### 🔍 Agent Decision Trace")
                    
                    # Display session-based agent trace
                    if result.get("session_id"):
                        from lifelens.ui.agent_trace import render_agent_trace_panel
                        from lifelens.utils.agent_utils import get_agent_trace, format_trace_for_ui
                        
                        try:
                            # Fetch trace data first
                            trace_data = get_agent_trace(client, result["session_id"])
                            if trace_data:
                                formatted_trace = format_trace_for_ui(trace_data)
                                render_agent_trace_panel(
                                    decisions=formatted_trace,
                                    title="🧠 Agent Reasoning Trace",
                                    expanded=False
                                )
                            else:
                                st.info("No agent trace data available for this session.")
                        except Exception as e:
                            st.error(f"Failed to load agent trace: {e}")
                            st.info("Session ID: " + result["session_id"])
                    else:
                        st.warning("No session ID available for this conversation.")
            
            # Show Evidence
            if result.get("sources"):
                with st.expander("📚 Retrieved Memories (Evidence)", expanded=False):
                    st.markdown(f"**Found {len(result['sources'])} relevant memories:**")
                    for idx, mem in enumerate(result["sources"], 1):
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"### Memory #{idx}")
                            with col2:
                                # Show similarity score and keyword matches
                                score = mem.get("score", 0)
                                score_color = "🟢" if score > 0.7 else "🟡" if score > 0.5 else "🔴"
                                st.caption(f"{score_color} Score: {score:.3f}")
                                if mem.get("keyword_matches"):
                                    st.caption(f"🔑 Matched: {', '.join(mem['keyword_matches'][:3])}")
                            
                            display_memory(mem)
                            st.markdown("---")
        
        # Display legacy mode memories if available
        elif "memories" in chat:
            with st.expander("View Retrieved Memories (Evidence)", expanded=False):
                if chat["memories"]:
                    for mem in chat["memories"]:
                        display_memory(mem)
                else:
                    st.write("No relevant memories found.")
    
    # Text or Voice Query
    query = st.chat_input("Ask about your memories...")
    
    # Use voice query if available
    if not query and st.session_state.get("voice_query"):
        query = st.session_state.voice_query
        st.session_state.voice_query = None
    
    if query:
        st.chat_message("user").write(query)
        
        with st.spinner("🤖 Multi-Agent System Processing..." if st.session_state.agentic_mode else "Thinking..."):
            # Use agentic flow or legacy flow
            if st.session_state.agentic_mode:
                # NEW: Multi-Agent Orchestrator Flow
                from lifelens.orchestrator import run_agentic_flow
                
                try:
                    result = run_agentic_flow(query, active_patient_id, client, max_retries=1)
                    
                    answer = result["answer"]
                    memories = result["sources"]
                    
                    # Display answer with AI indicator
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(answer)
                    
                    # Display comprehensive agent workflow
                    with st.expander("🔍 Agent Workflow & Analysis", expanded=False):
                        # Create tabs for different agent outputs
                        agent_tab1, agent_tab2, agent_tab3, agent_tab4, agent_tab5 = st.tabs([
                            "📋 Planner", "✅ Critic", "🔔 Triggers", "💡 Recommendations", "🔍 Agent Trace"
                        ])
                        
                        with agent_tab1:
                            st.markdown("### Planner Agent Decision")
                            st.json(result["plan"])
                            
                            # Explain the plan
                            st.markdown("**Reasoning:**")
                            st.info(result["plan"].get("reasoning", "No reasoning provided"))
                            
                            # Show retrieval decision
                            if result["plan"].get("retrieve", True):
                                st.success(f"✅ Retrieved {len(memories)} memories")
                            else:
                                st.info("ℹ️ No retrieval needed (direct answer)")
                        
                        with agent_tab2:
                            st.markdown("### Critic Agent Evaluation")
                            verdict_emoji = {
                                "OK": "✅",
                                "RETRY_RETRIEVAL": "🔄",
                                "SUGGEST_TRIGGER": "💡",
                                "REQUEST_MORE_DATA": "📥"
                            }
                            verdict_desc = {
                                "OK": "Answer is well-grounded and confident",
                                "RETRY_RETRIEVAL": "Memories not relevant, retried search",
                                "SUGGEST_TRIGGER": "Answer is weak, suggest capturing more data",
                                "REQUEST_MORE_DATA": "Not enough memories to answer confidently"
                            }
                            
                            st.markdown(f"**Verdict:** {verdict_emoji.get(result['verdict'], '❓')} {result['verdict']}")
                            st.info(verdict_desc.get(result['verdict'], "Unknown verdict"))
                            
                            if result["retry_count"] > 0:
                                st.warning(f"🔄 Retried {result['retry_count']} time(s) to improve answer quality")
                        
                        with agent_tab3:
                            st.markdown("### Trigger Agent Suggestions")
                            if result["triggers"]:
                                for idx, trigger in enumerate(result["triggers"], 1):
                                    priority_color = {
                                        "urgent": "🔴",
                                        "high": "🟠",
                                        "medium": "🟡",
                                        "low": "🟢"
                                    }
                                    priority_icon = priority_color.get(trigger.get("priority", "medium"), "🔵")
                                    
                                    with st.container():
                                        st.markdown(f"**{priority_icon} Trigger #{idx}**")
                                        st.write(trigger.get("message", "Notification"))
                                        st.caption(f"Type: {trigger.get('type', 'unknown')} | Priority: {trigger.get('priority', 'medium')}")
                                        st.markdown("---")
                            else:
                                st.success("✅ No triggers needed - everything looks good!")
                        
                        with agent_tab4:
                            st.markdown("### Recommender Agent Suggestions")
                            if result.get("recommendations"):
                                for idx, rec in enumerate(result["recommendations"], 1):
                                    st.info(f"**{idx}.** {rec.get('message', 'Suggestion')}")
                            else:
                                st.info("No specific capture recommendations at this time.")
                        
                        with agent_tab5:
                            st.markdown("### 🔍 Agent Decision Trace")
                            
                            # Display session-based agent trace
                            if result.get("session_id"):
                                from lifelens.ui.agent_trace import render_agent_trace_panel
                                from lifelens.utils.agent_utils import get_agent_trace, format_trace_for_ui
                                
                                try:
                                    # Fetch trace data first
                                    trace_data = get_agent_trace(client, result["session_id"])
                                    if trace_data:
                                        formatted_trace = format_trace_for_ui(trace_data)
                                        render_agent_trace_panel(
                                            decisions=formatted_trace,
                                            title="🧠 Agent Reasoning Trace",
                                            expanded=False
                                        )
                                    else:
                                        st.info("No agent trace data available for this session.")
                                except Exception as e:
                                    st.error(f"Failed to load agent trace: {e}")
                                    st.info("Session ID: " + result["session_id"])
                            else:
                                st.warning("No session ID available for this conversation.")
                    
                    # TTS Playback
                    from lifelens.utils.tts import text_to_speech
                    try:
                        with st.spinner("Speaking..."):
                            audio_bytes = text_to_speech(answer)
                            if audio_bytes:
                                st.audio(audio_bytes, format='audio/mp3', start_time=0)
                    except Exception:
                        pass
                    
                    # Show Evidence
                    with st.expander("📚 Retrieved Memories (Evidence)", expanded=False):
                        if memories:
                            st.markdown(f"**Found {len(memories)} relevant memories:**")
                            for idx, mem in enumerate(memories, 1):
                                with st.container():
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"### Memory #{idx}")
                                    with col2:
                                        # Show similarity score and keyword matches for debugging
                                        score = mem.get("score", 0)
                                        score_color = "🟢" if score > 0.7 else "🟡" if score > 0.5 else "🔴"
                                        st.caption(f"{score_color} Score: {score:.3f}")
                                        if mem.get("keyword_matches"):
                                            st.caption(f"🔑 Matched: {', '.join(mem['keyword_matches'][:3])}")
                                    
                                    display_memory(mem)
                                    
                                    # Show related memories
                                    from lifelens.utils.memory_graph import find_related_memories
                                    
                                    # Fetch all memories for relationship detection, excluding agent decisions
                                    all_results = client.scroll(
                                        collection_name=QDRANT_COLLECTION_NAME,
                                        limit=100,
                                        with_payload=True,
                                        with_vectors=False,
                                        scroll_filter=models.Filter(
                                            must=[
                                                models.FieldCondition(
                                                    key="patient_id",
                                                    match=models.MatchValue(value=active_patient_id)
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
                                    all_memories = [p.payload for p in all_results]
                                    
                                    related = find_related_memories(all_memories, mem)
                                    
                                    if related:
                                        st.markdown("**🔗 Related Memories:**")
                                        for rel in related[:3]:  # Show top 3
                                            st.caption(f"• {rel['reason']}")
                                    
                                    st.markdown("---")
                        else:
                            st.warning("⚠️ No memories retrieved!")
                            st.markdown("""
                            **Possible reasons:**
                            - Query keywords don't match stored memory content
                            - Images uploaded without text extraction (old screenshots)
                            - Try different or simpler keywords
                            - Check if memory exists in Dashboard → Memory Map
                            
                            **Tip:** For screenshots, re-upload them to enable text extraction, or add manual text notes describing them.
                            """)
                    
                    # Save to chat history
                    st.session_state.chat_history.append({
                        "query": query,
                        "answer": answer,
                        "result": result
                    })
                    
                except Exception as e:
                    st.error(f"Agentic flow error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    # Fallback to legacy flow
                    st.warning("Falling back to legacy mode...")
                    st.session_state.agentic_mode = False
                    st.rerun()
            
            else:
                # LEGACY: Original Flow
                # 1. Parse Time Filters
                time_filters = parse_time_filter(query)
                
                # 2. Add mood and type filters if selected
                if filter_mood:
                    if not time_filters:
                        time_filters = {}
                    time_filters['mood'] = filter_mood
                
                if filter_type:
                    if not time_filters:
                        time_filters = {}
                    time_filters['type'] = filter_type
                
                # 3. Retrieve Memories (filtered by patient_id, mood, type)
                memories = search_memories(client, query, filters=time_filters, patient_id=active_patient_id)
                
                # 4. Generate Answer
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
                
                # Show Evidence
                with st.expander("View Retrieved Memories (Evidence)"):
                    if memories:
                        for mem in memories:
                            display_memory(mem)
                            
                            # Show related memories
                            from lifelens.utils.memory_graph import find_related_memories
                            
                            # Fetch all memories for relationship detection, excluding agent decisions
                            all_results = client.scroll(
                                collection_name=QDRANT_COLLECTION_NAME,
                                limit=100,
                                with_payload=True,
                                with_vectors=False,
                                scroll_filter=models.Filter(
                                    must=[
                                        models.FieldCondition(
                                            key="patient_id",
                                            match=models.MatchValue(value=active_patient_id)
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
                            all_memories = [p.payload for p in all_results]
                            
                            related = find_related_memories(all_memories, mem)
                            
                            if related:
                                st.markdown("**🔗 Related Memories:**")
                                for rel in related[:3]:  # Show top 3
                                    st.caption(f"• {rel['reason']}")
                    else:
                        st.write("No relevant memories found.")
                
                # Save to chat history
                st.session_state.chat_history.append({
                    "query": query,
                    "answer": answer,
                    "memories": memories
                })

# --- TAB 3: MEMORY LANE ---
with tab3:
    st.header("Memory Lane")
    st.write("Recent memories stored in LifeLens.")
    
    refresh = st.button("Refresh Timeline")
    
    # Show initial or refreshed list
    results = client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=50,
        with_payload=True,
        with_vectors=False,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="patient_id",
                    match=models.MatchValue(value=active_patient_id)
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
    
    if results:
        # Sort by timestamp descending
        sorted_points = sorted(
            results, 
            key=lambda x: x.payload.get('timestamp', 0), 
            reverse=True
        )
        
        for point in sorted_points:
            mem_dict = point.payload
            display_memory(mem_dict)
    else:
        st.info("No memories found! Upload some in the 'Remember This' tab.")
