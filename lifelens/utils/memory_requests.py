import json
import os
from datetime import datetime

REQUESTS_FILE = "memory_requests.json"

def load_requests():
    """Load memory requests from JSON file."""
    if os.path.exists(REQUESTS_FILE):
        try:
            with open(REQUESTS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_requests(requests):
    """Save memory requests to JSON file."""
    with open(REQUESTS_FILE, "w") as f:
        json.dump(requests, f, indent=2)

def create_request(patient_id, requester_name, memory_type, description, details=None):
    """
    Create a new memory request from family member.
    
    Args:
        patient_id: ID of the patient
        requester_name: Name of family member making request
        memory_type: Type of memory (achievement, event, milestone)
        description: Description of the memory to add
        details: Additional details (location, date, people involved)
    
    Returns:
        Request ID
    """
    requests = load_requests()
    
    request_id = f"req_{len(requests) + 1}_{int(datetime.now().timestamp())}"
    
    new_request = {
        "id": request_id,
        "patient_id": patient_id,
        "requester_name": requester_name,
        "memory_type": memory_type,
        "description": description,
        "details": details or {},
        "status": "pending",  # pending, approved, completed, rejected
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    requests.append(new_request)
    save_requests(requests)
    
    return request_id

def get_requests_for_patient(patient_id, status=None):
    """Get all requests for a specific patient, optionally filtered by status."""
    requests = load_requests()
    filtered = [r for r in requests if r["patient_id"] == patient_id]
    
    if status:
        filtered = [r for r in filtered if r["status"] == status]
    
    return filtered

def update_request_status(request_id, new_status, notes=None):
    """Update the status of a memory request."""
    requests = load_requests()
    
    for req in requests:
        if req["id"] == request_id:
            req["status"] = new_status
            req["updated_at"] = datetime.now().isoformat()
            if notes:
                req["notes"] = notes
            break
    
    save_requests(requests)

def delete_request(request_id):
    """Delete a memory request."""
    requests = load_requests()
    requests = [r for r in requests if r["id"] != request_id]
    save_requests(requests)
