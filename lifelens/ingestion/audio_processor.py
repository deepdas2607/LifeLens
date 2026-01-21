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
        
        # Analyze Sentiment
        sentiment = "Neutral"
        try:
            chat_completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Classify the sentiment of the following text as exactly one of: Happy, Sad, Angry, Confused, Neutral. Return only the word."},
                    {"role": "user", "content": transcript}
                ],
                max_tokens=10
            )
            sentiment = chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Sentiment Analysis Failed: {e}")

        # Read back for base64
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
            audio_str = base64.b64encode(audio_bytes).decode()
            
        return {
            "transcript": transcript,
            "sentiment": sentiment,
            "base64": audio_str
        }

    except Exception as e:
        raise RuntimeError(f"Processing failed: {e}")

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
