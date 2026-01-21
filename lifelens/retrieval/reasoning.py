import os
from groq import Groq
from lifelens.config import GROQ_API_KEY

def get_answer(query: str, memories: list) -> str:
    """
    Generates an answer using Groq LLaMA 3 based on retrieved memories.
    """
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY is not set."

    client = Groq(api_key=GROQ_API_KEY)

    # Format Memories for Context
    memory_context = ""
    for idx, mem in enumerate(memories):
        mem_type = mem.get('type')
        content = ""
        if mem_type == 'image':
            content = f"Image Caption: {mem.get('caption')}"
        elif mem_type == 'audio':
            content = f"Audio Transcript: {mem.get('transcript')}"
        elif mem_type == 'text':
            content = f"Note: {mem.get('content')}"
            
        timestamp = mem.get('timestamp')
        # specific string format for timestamp could be added here if needed
            
        memory_context += f"{idx+1}. [{mem_type.upper()}] {content} (Timestamp: {timestamp})\n"

    system_prompt = f"""
You are LifeLens, an AI memory assistant.

Your job:
- Only use retrieved memories.
- Never guess or hallucinate.
- Include timestamps when available.
- When referencing images, say "In the stored photo, ..."
- When referencing audio, say "From your audio note, ..."

User Query:
{query}

Retrieved Memories:
{memory_context}

Generate a helpful, safe, grounded answer.
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        return f"Error generating answer: {str(e)}"
