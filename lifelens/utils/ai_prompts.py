from groq import Groq
from lifelens.config import GROQ_API_KEY
from datetime import datetime, timedelta

def generate_ai_prompts(recent_memories, last_upload_time):
    """
    Generate contextual AI prompts based on user activity.
    """
    prompts = []
    
    # Check upload frequency
    if last_upload_time:
        days_since = (datetime.now() - datetime.fromtimestamp(last_upload_time)).days
        
        if days_since >= 3:
            prompts.append({
                "type": "encouragement",
                "message": f"It's been {days_since} days since your last memory. Would you like to capture a moment today?"
            })
    
    # Suggest based on recent memories
    if recent_memories:
        memory_types = [m.get("type") for m in recent_memories]
        
        if "image" not in memory_types:
            prompts.append({
                "type": "suggestion",
                "message": "📸 Try uploading a photo to capture visual memories!"
            })
        
        if "audio" not in memory_types:
            prompts.append({
                "type": "suggestion",
                "message": "🎤 Record a voice note to preserve your thoughts!"
            })
    
    # LLM-generated contextual prompt
    if GROQ_API_KEY and recent_memories:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            
            # Summarize recent activity
            summary = f"Recent memories: {len(recent_memories)} items. "
            summary += f"Types: {', '.join(set([m.get('type') for m in recent_memories[:5]]))}"
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Generate a warm, encouraging prompt for a dementia patient to upload a new memory. Keep it under 20 words."},
                    {"role": "user", "content": summary}
                ],
                max_tokens=50
            )
            
            ai_prompt = completion.choices[0].message.content.strip()
            prompts.append({
                "type": "ai_suggestion",
                "message": f"💡 {ai_prompt}"
            })
        except:
            pass
    
    return prompts
