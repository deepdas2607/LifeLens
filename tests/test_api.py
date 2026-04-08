import google.generativeai as genai
import time
import os
import sys

# Add parent directory to path to import lifelens
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lifelens.config import GEMINI_API_KEY

def test_video():
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        return

    genai.configure(api_key=GEMINI_API_KEY)

    # List available models again to be sure
    print("--- Available Models ---")
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for m in models:
        print(m)
    print("------------------------")

    # Create a dummy video file (using a small text file pretending to be video for upload check, 
    # but preferably we need a real video. 
    # Since I cannot easily create a valid mp4 without opencv/ffmpeg, 
    # I will try to use the model generation on a simple text prompt first to verify the model name *validity* for generation)
    
    target_model = 'gemini-flash-latest'
    print(f"\nTesting Text Generation with '{target_model}'...")
    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content("Hello, this is a test.")
        print(f"[SUCCESS] Text Generation Success: {response.text}")
    except Exception as e:
        print(f"[FAIL] Text Generation Failed: {e}")
        try:
            print(f"Retrying with 'models/{target_model}'...")
            model = genai.GenerativeModel(f'models/{target_model}')
            response = model.generate_content("Hello, this is a test.")
            print(f"[SUCCESS] Text Generation Success with prefix: {response.text}")
        except Exception as e2:
            print(f"[FAIL] Text Generation Failed with prefix: {e2}")

    print("\nNote: If text generation works but video fails, it is a file-API specific issue.")

if __name__ == "__main__":
    test_video()
