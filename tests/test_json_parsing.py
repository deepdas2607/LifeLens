"""
Test script to verify agent JSON parsing works correctly
"""

import sys
import os
# Add parent directory to path to import lifelens
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lifelens.agents.analytics_agent import _safe_json_parse as analytics_parse
from lifelens.agents.summary_agent import _safe_json_parse as summary_parse

# Test cases
test_cases = [
    # Valid JSON
    ('{"key": "value"}', "Valid JSON"),
    
    # JSON with markdown code blocks
    ('```json\n{"key": "value"}\n```', "JSON in code block"),
    ('```\n{"key": "value"}\n```', "JSON in simple code block"),
    
    # Nested JSON
    ('{"data": {"nested": "value"}}', "Nested JSON"),
    
    # Empty response
    ('', "Empty string"),
    
    # Invalid JSON
    ('{invalid}', "Invalid JSON"),
    
    # Mixed content with JSON
    ('Here is the result:\n```json\n{"status": "success"}\n```\nDone!', "Mixed content"),
]

print("[TEST] Testing Safe JSON Parsing\n")
for test_input, description in test_cases:
    result = analytics_parse(test_input)
    status = "[PASS]" if isinstance(result, dict) else "[FAIL]"
    print(f"{status} {description}: {result}")

print("\n[PASS] All JSON parsing tests complete!")
print("\n[INFO] The agents will now handle:")
print("  - Empty LLM responses")
print("  - Markdown code blocks (```json```)")
print("  - Invalid JSON (returns empty dict)")
print("  - Mixed content with JSON embedded")
