import google.generativeai as genai
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from lifelens.config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is missing in config.")
        sys.exit(1)

    genai.configure(api_key=GEMINI_API_KEY)
    
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            
except Exception as e:
    print(f"Error: {e}")
