import os
import base64
import tempfile
from groq import Groq
from lifelens.config import GROQ_API_KEY

def process_audio(audio_file):
    """
    Process an uploaded audio file:
    1. Transcribe using Groq Whisper API (distil-whisper-large-v3-en).
    2. Return the transcript and base64 encoded audio.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")
    
    client = Groq(api_key=GROQ_API_KEY)
    
    # Save to temp file because Groq client needs a file-like object or path
    # We'll use the file object directly if possible, or save temp if needed.
    # Streamlit UploadedFile is file-like.
    
    # However, Groq python client usually expects a filename or a tuple (filename, file-like)
    # Let's save to temp to be safe and avoid format issues.
    
    # Determine if input is a path or file-like object
    if isinstance(audio_file, str) and os.path.exists(audio_file):
        # It's a file path
        temp_path = audio_file
        # We don't need to write to a new temp file if it's already a path
        # But we need to ensure it persists if logic expects a temp file context?
        # The logic below uses `temp_path`.
        
        # Read for extension check if needed, but whisper handles it.
    else:
        # It's a Streamlit UploadedFile or BytesIO
        # Determine extension
        ext = ".wav"
        if hasattr(audio_file, "name"):
             _, ext = os.path.splitext(audio_file.name)
             if not ext: ext = ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_audio:
            temp_audio.write(audio_file.getvalue())
            temp_path = temp_audio.name

    try:
        with open(temp_path, "rb") as file_obj:
            transcription = client.audio.transcriptions.create(
                file=(temp_path, file_obj.read()),
                model="whisper-large-v3",
                response_format="json",
                language="en",
                temperature=0.0
            )
        
        transcript = transcription.text
        
        # Analyze Mood (more nuanced than basic sentiment)
        mood = "neutral"
        mood_confidence = 0.0
        try:
            chat_completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": """You are an emotion detection AI. Analyze the text and classify the primary mood.

Output ONLY the mood word from this list:
happy, excited, content, calm, neutral, anxious, confused, sad, angry, depressed, frustrated, lonely, worried

Be sensitive to subtle emotional cues. Consider context and word choice."""},
                    {"role": "user", "content": transcript}
                ],
                max_tokens=10,
                temperature=0.1
            )
            mood = chat_completion.choices[0].message.content.strip().lower()
            
            # Validate mood
            valid_moods = ["happy", "excited", "content", "calm", "neutral", "anxious", 
                          "confused", "sad", "angry", "depressed", "frustrated", "lonely", "worried"]
            if mood not in valid_moods:
                mood = "neutral"
                
        except Exception as e:
            print(f"Mood Analysis Failed: {e}")
            mood = "neutral"

        # Read back for base64
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
            audio_str = base64.b64encode(audio_bytes).decode()
            
        return {
            "transcript": transcript,
            "mood": mood,
            "sentiment": mood.capitalize(),  # Backward compatibility
            "audio_base64": audio_str
        }

    except Exception as e:
        raise RuntimeError(f"Processing failed: {e}")

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
