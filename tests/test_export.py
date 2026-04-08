"""
Test mood data export functionality
"""
import sys
import os
# Add parent directory to path to import lifelens
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lifelens.qdrant.client import get_qdrant_client
from lifelens.ui.mood_components import _export_mood_data, _convert_to_csv

print("="*70)
print("  TESTING MOOD DATA EXPORT")
print("="*70)

client = get_qdrant_client()
patient_id = "patient_1"

print(f"\nExporting mood data for: {patient_id}")

# Test JSON export
export_data = _export_mood_data(client, patient_id)

if export_data:
    print(f"\n[SUCCESS] Export successful!")
    print(f"   - Total Events: {export_data['total_events']}")
    print(f"   - Total Alerts: {export_data['total_alerts']}")
    print(f"   - Export Time: {export_data['export_timestamp']}")
    
    # Test CSV conversion
    csv_data = _convert_to_csv(export_data)
    csv_lines = csv_data.split('\n')
    print(f"\n[SUCCESS] CSV conversion successful!")
    print(f"   - CSV Lines: {len(csv_lines)}")
    print(f"\nFirst 10 lines of CSV:")
    print("-" * 70)
    for line in csv_lines[:10]:
        print(line)
    
    # Save sample files
    import json
    with open("sample_export.json", "w") as f:
        json.dump(export_data, f, indent=2)
    with open("sample_export.csv", "w") as f:
        f.write(csv_data)
    
    print("\n" + "="*70)
    print("[SUCCESS] Sample files saved:")
    print("   - sample_export.json")
    print("   - sample_export.csv")
else:
    print("\n[FAIL] Export failed - no data available")

print("\n" + "="*70)
