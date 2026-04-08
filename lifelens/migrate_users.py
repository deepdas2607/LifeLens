import sys
import os
import logging
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lifelens.auth.users import load_users, save_user_to_qdrant, ensure_qdrant_user_collection

# Configure logging
logging.basicConfig(level=logging.INFO)

def migrate():
    print("🚀 Starting User Migration to Qdrant...")
    
    # 1. Ensure collection exists
    print("Checking Qdrant collection...")
    ensure_qdrant_user_collection()
    
    # 2. Load users
    users = load_users()
    if not users:
        print("No users found in users.json to migrate.")
        return

    print(f"Found {len(users)} users. Syncing...")
    
    # 3. Sync
    success_count = 0
    for username, data in tqdm(users.items()):
        try:
            save_user_to_qdrant(username, data)
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to migrate {username}: {e}")
            
    print(f"✅ Migration Complete! Synced {success_count}/{len(users)} users.")

if __name__ == "__main__":
    migrate()
