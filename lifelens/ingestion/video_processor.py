import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY
import tempfile
import os
import time

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def process_video(video_file):
    """
    Process an uploaded video:
    1. Upload to Gemini File API.
    2. Wait for processing.
    3. Analyze with Gemini 1.5 Flash (video understanding).
    4. Return summary, mood, people.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Save to temp file for upload
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_file.getvalue())
        tmp_path = tmp.name

    try:
        # Upload to Gemini
        print(f"Uploading video: {tmp_path}")
        gemini_file = genai.upload_file(tmp_path, mime_type="video/mp4")
        
        # Wait for processing
        while gemini_file.state.name == "PROCESSING":
            time.sleep(1)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name == "FAILED":
            raise ValueError("Gemini video processing failed.")

        # Analyze
        model = genai.GenerativeModel('gemini-flash-latest')
        prompt = """Analyze this video segment from a wearable camera.
        Provide a friendly, human-readable description.
        
        Structure your response like this:
        **Summary**: [What is happening]
        **Mood**: [The vibe of the scene]
        **People**: [Who is visible]
        **Key Objects**: [Important items]
        
        Be detailed but natural."""
        
        response = model.generate_content([prompt, gemini_file])
        
        # Cleanup
        genai.delete_file(gemini_file.name)
        
        return {
            "analysis": response.text,
            "file_path": tmp_path
        }

    finally:
        # In a real app we'd upload to S3/GCS. For now, we leave the temp file? 
        # Or maybe we rely on the caller to handle file persistence. 
        # The task doesn't specify persistent video storage (S3), just Qdrant for metadata.
        # We'll return the path, but standard tempfiles on Windows are tricky.
        pass
