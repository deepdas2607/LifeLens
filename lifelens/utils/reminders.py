from groq import Groq
from lifelens.config import GROQ_API_KEY
import json
import os

REMINDERS_FILE = "reminders.json"

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_reminder(reminder):
    reminders = load_reminders()
    reminders.append(reminder)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f)

def extract_reminder(text):
    """
    Uses LLM to check if the text contains a future task.
    Returns dict or None.
    """
    if not GROQ_API_KEY:
        return None
        
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = f"""
    Analyze the following text. Does it contain a future task, appointment, or reminder?
    If yes, return a JSON object with keys "task" (short description) and "time" (when it is due).
    If no, return {{ "is_reminder": false }}.
    
    Text: "{text}"
    
    Return ONLY VALID JSON.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts reminders to JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(completion.choices[0].message.content)
        
        if result.get("is_reminder") is False:
            return None
            
        # Check if task key exists (sometimes LLM structure varies slightly despite instructions)
        if "task" in result:
            return result
            
        return None
        
    except Exception as e:
        print(f"Reminder Extraction Error: {e}")
        return None
