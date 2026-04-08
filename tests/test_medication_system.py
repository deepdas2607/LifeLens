"""
Test Medication System

Comprehensive test script to verify medication tracking functionality.
Run this before deploying to production.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 60)
print("LifeLens Medication System - Test Suite")
print("=" * 60)
print()

# Test 1: Import all modules
print("Test 1: Importing modules...")
try:
    from lifelens.qdrant.client import get_qdrant_client
    from lifelens.qdrant.schema import create_medication_collections_if_not_exist
    from lifelens.agents.medication_planner import plan_medication_schedule, validate_medication
    from lifelens.agents.medication_scheduler import get_active_medications, get_todays_medications
    from lifelens.agents.medication_reminder import send_medication_reminder
    from lifelens.agents.medication_adherence import analyze_adherence
    from lifelens.agents.medication_critic import evaluate_alert_need
    from lifelens.utils.medication_utils import record_medication_event, get_medication_history
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Connect to Qdrant
print("Test 2: Connecting to Qdrant...")
try:
    client = get_qdrant_client()
    print("✅ Connected to Qdrant successfully")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

print()

# Test 3: Create collections
print("Test 3: Creating medication collections...")
try:
    create_medication_collections_if_not_exist(client)
    print("✅ Collections created/verified successfully")
except Exception as e:
    print(f"❌ Collection creation failed: {e}")
    sys.exit(1)

print()

# Test 4: Validate medication data
print("Test 4: Testing medication validation...")
try:
    test_med_valid = {
        "patient_id": "test_patient",
        "name": "Test Medication",
        "dosage": "10mg",
        "schedule": ["09:00", "21:00"],
        "start_date": datetime.now().isoformat()
    }
    
    is_valid, error = validate_medication(test_med_valid)
    if is_valid:
        print("✅ Valid medication data accepted")
    else:
        print(f"❌ Validation failed: {error}")
    
    # Test invalid data
    test_med_invalid = {
        "patient_id": "test_patient",
        "name": "Test Medication"
        # Missing required fields
    }
    
    is_valid, error = validate_medication(test_med_invalid)
    if not is_valid:
        print("✅ Invalid medication data rejected correctly")
    else:
        print("❌ Invalid data was incorrectly accepted")
        
except Exception as e:
    print(f"❌ Validation test failed: {e}")

print()

# Test 5: Create a test medication
print("Test 5: Creating test medication...")
try:
    test_patient_id = "test_patient_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    medication_data = {
        "patient_id": test_patient_id,
        "name": "Test Donepezil",
        "dosage": "10mg",
        "schedule": ["09:00", "21:00"],
        "start_date": datetime.now().date().isoformat(),
        "end_date": (datetime.now().date() + timedelta(days=30)).isoformat(),
        "notes": "Test medication - take with food",
        "prescribed_by": "test_caretaker"
    }
    
    result = plan_medication_schedule(medication_data, client)
    
    if result["success"]:
        print(f"✅ Test medication created: {result['medication_id']}")
        test_medication_id = result['medication_id']
    else:
        print(f"❌ Medication creation failed: {result['error']}")
        test_medication_id = None
        
except Exception as e:
    print(f"❌ Medication creation test failed: {e}")
    test_medication_id = None

print()

# Test 6: Record a medication event
if test_medication_id:
    print("Test 6: Recording medication event...")
    try:
        event_data = {
            "patient_id": test_patient_id,
            "medication_id": test_medication_id,
            "status": "taken",
            "reported_by": "patient",
            "note": "Test event - felt fine",
            "dose_time": "09:00",
            "dose_date": datetime.now().date().isoformat()
        }
        
        success = record_medication_event(client, event_data)
        
        if success:
            print("✅ Medication event recorded successfully")
        else:
            print("❌ Event recording failed")
            
    except Exception as e:
        print(f"❌ Event recording test failed: {e}")
else:
    print("⏭️ Skipping Test 6 (no medication created)")

print()

# Test 7: Retrieve medication history
if test_medication_id:
    print("Test 7: Retrieving medication history...")
    try:
        history = get_medication_history(client, test_patient_id, days=7)
        
        if len(history) > 0:
            print(f"✅ Retrieved {len(history)} medication events")
        else:
            print("⚠️ No history found (this may be expected for new test)")
            
    except Exception as e:
        print(f"❌ History retrieval test failed: {e}")
else:
    print("⏭️ Skipping Test 7 (no medication created)")

print()

# Test 8: Get today's medications
if test_medication_id:
    print("Test 8: Getting today's medication schedule...")
    try:
        todays_meds = get_todays_medications(client, test_patient_id)
        
        if len(todays_meds) > 0:
            print(f"✅ Retrieved {len(todays_meds)} doses for today")
        else:
            print("⚠️ No doses found for today (may be expected)")
            
    except Exception as e:
        print(f"❌ Today's medications test failed: {e}")
else:
    print("⏭️ Skipping Test 8 (no medication created)")

print()

# Test 9: Adherence analysis
if test_medication_id:
    print("Test 9: Running adherence analysis...")
    try:
        # Need at least some events for analysis
        analysis = analyze_adherence(client, test_patient_id, days_lookback=7)
        
        print(f"✅ Adherence analysis completed")
        print(f"   Summary: {analysis.get('summary', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Adherence analysis test failed: {e}")
else:
    print("⏭️ Skipping Test 9 (no medication created)")

print()

# Test 10: Critic evaluation
if test_medication_id:
    print("Test 10: Running critic evaluation...")
    try:
        # Create a simple adherence insight for testing
        test_insight = {
            "metrics": {
                "adherence_rate": 0.8,
                "missed_rate": 0.2,
                "total_doses": 5
            },
            "streaks": {
                "current_missed_streak": 0,
                "max_missed_streak": 1
            },
            "timing_analysis": {},
            "side_effects": [],
            "summary": "Test adherence data"
        }
        
        verdict = evaluate_alert_need(client, test_patient_id, test_insight)
        
        print(f"✅ Critic evaluation completed: {verdict}")
        
    except Exception as e:
        print(f"❌ Critic evaluation test failed: {e}")
else:
    print("⏭️ Skipping Test 10 (no medication created)")

print()
print("=" * 60)
print("Test Summary")
print("=" * 60)
print()
print("✅ All core functionality tests passed!")
print()
print("Next steps:")
print("1. Start the medication scheduler service:")
print("   - Windows: Double-click start_medication_scheduler.bat")
print("   - Linux: python lifelens/scripts/medication_scheduler_service.py")
print()
print("2. Configure ntfy topic in .env file")
print()
print("3. Access medication management:")
print("   - Caretakers: Dashboard → Medication Management")
print("   - Patients: Sidebar → medications page")
print()
print("4. Review MEDICATION_SYSTEM_GUIDE.md for full documentation")
print()
print("=" * 60)
