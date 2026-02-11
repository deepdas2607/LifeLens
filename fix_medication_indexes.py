"""
Fix script to ensure all required indexes exist on medication collections
Run this to fix the medication_id index error
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from lifelens.qdrant.client import get_qdrant_client
from lifelens.qdrant.schema import create_medication_collections_if_not_exist
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_medication_indexes():
    """Ensure all medication indexes exist"""
    logger.info("Fixing medication collection indexes...")
    
    try:
        client = get_qdrant_client()
        logger.info("✅ Connected to Qdrant")
        
        # This will now create indexes even if collections exist
        create_medication_collections_if_not_exist(client)
        
        logger.info("✅ Medication indexes fixed!")
        logger.info("\nYou can now run the medication scheduler without errors.")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_medication_indexes()
    if success:
        print("\n" + "="*60)
        print("✅ Medication indexes are now properly configured!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Failed to fix indexes. Check errors above.")
        print("="*60)
