import json
import os
import hashlib
import uuid
import logging
from lifelens.qdrant.client import get_qdrant_client
from lifelens.qdrant.schema import create_user_collection_if_not_exists
from lifelens.config import QDRANT_USER_COLLECTION_NAME
from qdrant_client.http import models

USERS_FILE = "users.json"

def hash_password(password):
    """Simple password hashing using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_qdrant_user_collection():
    """Ensures Qdrant collection exists."""
    try:
        client = get_qdrant_client()
        create_user_collection_if_not_exists(client)
    except Exception as e:
        logging.error(f"Could not init Qdrant user collection: {e}")

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
    
    # Dual-write to Qdrant
    try:
        save_user_to_qdrant(username, users[username])
    except Exception as e:
        logging.error(f"Failed to save user to Qdrant: {e}")
        
    return True, "User created successfully"

def save_user_to_qdrant(username, user_data):
    """Syncs a user to Qdrant."""
    client = get_qdrant_client()
    
    # Deterministic ID based on username
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, username))
    
    payload = {
        "username": username,
        "password": user_data["password"], # Hashed
        "role": user_data["role"],
        "full_name": user_data["full_name"],
        "patient_id": user_data["patient_id"]
    }
    
    client.upsert(
        collection_name=QDRANT_USER_COLLECTION_NAME,
        points=[models.PointStruct(
            id=point_id,
            vector=[0.0], # Dummy vector
            payload=payload
        )]
    )
    logging.info(f"User '{username}' synced to Qdrant.")

def authenticate(username, password):
    """
    Authenticate user.
    Strategy: Try Qdrant first -> Fallback to JSON.
    """
    hashed_pw = hash_password(password)
    
    # 1. Try Qdrant
    try:
        client = get_qdrant_client()
        # Scroll for username match
        results = client.scroll(
            collection_name=QDRANT_USER_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="username", match=models.MatchValue(value=username))]
            ),
            limit=1
        )[0]
        
        if results:
            user_data = results[0].payload
            if user_data["password"] == hashed_pw:
                logging.info(f"User '{username}' authenticated via Qdrant.")
                return {
                    "username": username,
                    "role": user_data["role"],
                    "full_name": user_data["full_name"],
                    "patient_id": user_data["patient_id"]
                }
    except Exception as e:
        logging.warning(f"Qdrant auth failed (falling back to JSON): {e}")

    # 2. Fallback to JSON
    users = load_users()
    
    if username not in users:
        return None
    
    user = users[username]
    if user["password"] == hashed_pw:
        logging.info(f"User '{username}' authenticated via JSON (Fallback).")
        # Optional: Heal Qdrant here?
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
