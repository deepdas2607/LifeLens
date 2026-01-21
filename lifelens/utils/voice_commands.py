from groq import Groq
from lifelens.config import GROQ_API_KEY
import tempfile
import os

def process_voice_command(audio_file):
    """
    Transcribe voice command and return the text.
    """
    if not GROQ_API_KEY:
        return None
    
    client = Groq(api_key=GROQ_API_KEY)
    
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
        
        return transcription.text

    except Exception as e:
        print(f"Voice command transcription failed: {e}")
        return None

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
