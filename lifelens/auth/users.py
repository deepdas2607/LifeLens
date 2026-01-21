import json
import os
import hashlib

USERS_FILE = "users.json"

def hash_password(password):
    """Simple password hashing using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load users from JSON file."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def create_user(username, password, role, full_name, patient_id=None):
    """
    Create a new user.
    Roles: 'patient', 'caretaker', 'family'
    patient_id: Required for caretaker/family, auto-generated for patient
    """
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    # Auto-generate patient_id for patients
    if role == "patient":
        patient_id = f"patient_{len([u for u in users.values() if u['role'] == 'patient']) + 1}"
    elif not patient_id:
        return False, "patient_id required for caretaker/family roles"
    
    users[username] = {
        "password": hash_password(password),
        "role": role,
        "full_name": full_name,
        "patient_id": patient_id
    }
    
    save_users(users)
    return True, "User created successfully"

def authenticate(username, password):
    """Authenticate user and return user data if successful."""
    users = load_users()
    
    if username not in users:
        return None
    
    user = users[username]
    if user["password"] == hash_password(password):
        return {
            "username": username,
            "role": user["role"],
            "full_name": user["full_name"],
            "patient_id": user["patient_id"]
        }
    
    return None

def get_all_patients():
    """Get list of all patients for caretaker/family to select."""
    users = load_users()
    patients = []
    
    for username, data in users.items():
        if data["role"] == "patient":
            patients.append({
                "patient_id": data["patient_id"],
                "full_name": data["full_name"],
                "username": username
            })
    
    return patients

def initialize_default_users():
    """Create default users if none exist."""
    users = load_users()
    
    if not users:
        # Create default patient
        create_user("patient1", "patient123", "patient", "John Doe")
        # Create default caretaker
        create_user("caretaker1", "care123", "caretaker", "Mary Smith", "patient_1")
        # Create default family member
        create_user("family1", "family123", "family", "Sarah Doe", "patient_1")
        
        return True
    return False
