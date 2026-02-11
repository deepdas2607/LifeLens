"""
Quick validation script for Mood Intelligence Agent components.
Tests that all files exist, have no syntax errors, and key functions are importable.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def test_imports():
    """Test that all mood intelligence modules can be imported."""
    print("\n=== Testing Module Imports ===\n")
    
    try:
        from lifelens.agents import mood_agent
        print("✓ mood_agent module imported")
        
        from lifelens.agents.critic import evaluate_mood_alert
        print("✓ critic.evaluate_mood_alert imported")
        
        from lifelens.ui import mood_components
        print("✓ mood_components module imported")
        
        from lifelens.qdrant.schema import create_mood_collections_if_not_exist
        print("✓ schema.create_mood_collections_if_not_exist imported")
        
        from lifelens.utils.ntfy_notifications import send_mood_alert
        print("✓ ntfy_notifications.send_mood_alert imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_key_functions():
    """Test that key functions exist and have proper signatures."""
    print("\n=== Testing Key Functions ===\n")
    
    try:
        from lifelens.agents.mood_agent import (
            calculate_risk_score,
            run_mood_analysis,
            store_mood_feedback,
            _convert_mood_to_score,
            _calculate_mood_slope,
            _detect_negative_streak
        )
        print("✓ All mood_agent functions present")
        
        # Test mood scoring
        test_moods = ["happy", "sad", "depressed", "neutral", "anxious"]
        for mood in test_moods:
            score = _convert_mood_to_score(mood)
            print(f"  • {mood}: {score:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_structure():
    """Verify all expected files exist."""
    print("\n=== Testing File Structure ===\n")
    
    # Get project root (parent of lifelens directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    files = [
        "lifelens/agents/mood_agent.py",
        "lifelens/ui/mood_components.py",
        "lifelens/test_mood_system.py",
        "lifelens/scripts/scheduled_mood_analysis.py",
        "MOOD_IMPLEMENTATION.md",
        "MOOD_QUICKSTART.md"
    ]
    
    all_exist = True
    for file_path in files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✓ {file_path} ({size} bytes)")
        else:
            print(f"✗ {file_path} NOT FOUND")
            print(f"  (Checked: {full_path})")
            all_exist = False
    
    return all_exist


def test_qdrant_connection():
    """Test connection to Qdrant (non-blocking)."""
    print("\n=== Testing Qdrant Connection ===\n")
    
    try:
        from lifelens.qdrant.client import get_qdrant_client
        client = get_qdrant_client()
        
        collections = client.get_collections()
        print(f"✓ Connected to Qdrant ({len(collections.collections)} collections)")
        
        # Check for mood collections
        collection_names = [c.name for c in collections.collections]
        for name in ["mood_events", "mood_alerts", "mood_feedback"]:
            if name in collection_names:
                print(f"  ✓ {name} collection exists")
            else:
                print(f"  ⚠ {name} collection not found (will be created on first use)")
        
        return True
    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
        print("  (Make sure Qdrant is running and configured in .env)")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  LifeLens Mood Intelligence Agent - Quick Validation")
    print("="*70)
    
    results = {
        "imports": test_imports(),
        "functions": test_key_functions(),
        "files": test_file_structure(),
        "qdrant": test_qdrant_connection()
    }
    
    print("\n" + "="*70)
    print("  Validation Summary")
    print("="*70 + "\n")
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name.title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All validation checks passed!")
        print("\nMood Intelligence Agent is properly installed and configured.")
        print("\nNext steps:")
        print("  1. Run full test: python -m lifelens.test_mood_system")
        print("  2. Start dashboard: streamlit run lifelens/app.py")
        print("  3. Upload mood memories and view insights\n")
        sys.exit(0)
    else:
        print("\n⚠ Some validation checks failed. Review errors above.\n")
        sys.exit(1)
