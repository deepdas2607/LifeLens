import streamlit as st

def init_session():
    """Initialize session state variables."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "active_patient_id" not in st.session_state:
        st.session_state.active_patient_id = None

def login(user_data):
    """Log in a user."""
    st.session_state.logged_in = True
    st.session_state.user = user_data
    
    # For patients, set their own patient_id as active
    if user_data["role"] == "patient":
        st.session_state.active_patient_id = user_data["patient_id"]
    # For caretaker/family, they'll select a patient

def logout():
    """Log out the current user."""
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.active_patient_id = None

def set_active_patient(patient_id):
    """Set the active patient for caretaker/family."""
    st.session_state.active_patient_id = patient_id

def get_current_user():
    """Get current logged-in user."""
    return st.session_state.get("user")

def get_active_patient_id():
    """Get the currently active patient ID."""
    return st.session_state.get("active_patient_id")

def is_logged_in():
    """Check if user is logged in."""
    return st.session_state.get("logged_in", False)

def has_dashboard_access():
    """Check if current user can access dashboard."""
    user = get_current_user()
    if not user:
        return False
    return user["role"] in ["caretaker", "family"]
