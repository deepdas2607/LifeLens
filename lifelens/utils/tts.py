from gtts import gTTS
import io

def text_to_speech(text):
    """
    Converts text to speech using gTTS and returns the audio bytes.
    """
    if not text:
        return None
    
    try:
        # Use 'com' tld for US English, fast speed False for clarity
        tts = gTTS(text=text, lang='en', tld='com', slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
