import os
from groq import Groq
from lifelens.config import GROQ_API_KEY

def get_answer(query: str, memories: list) -> str:
    """
    Generates an answer using Groq LLaMA 3 based on retrieved memories.
    """
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY is not set."
    
    # CRITICAL: Refuse to answer if no memories are found
    if not memories or len(memories) == 0:
        return "I couldn't find any relevant memories to answer your question. Please try rephrasing your query or add more memories to your collection."

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
        elif mem_type == 'video':
            content = f"Video Analysis: {mem.get('analysis')}"
            
        timestamp = mem.get('timestamp')
        
        # Add person tags if available
        person_info = ""
        if mem.get('person_tags'):
            person_info = f" | People: {mem.get('person_tags')}"
        
        # Add location if available
        location_info = ""
        if mem.get('location'):
            loc = mem.get('location')
            if isinstance(loc, dict):
                location_info = f" | Location: {loc.get('name', str(loc.get('lat')) + ', ' + str(loc.get('lon')))}"
            
        memory_context += f"{idx+1}. [{mem_type.upper()}] {content}{person_info}{location_info} (Timestamp: {timestamp})\n"

    system_prompt = f"""
You are LifeLens, an AI memory assistant.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:
1. ONLY use the retrieved memories provided below. DO NOT use any external knowledge.
2. If the retrieved memories don't contain information to answer the question, say "I don't have any memories about that."
3. NEVER guess, assume, or hallucinate information.
4. NEVER provide general knowledge or information not in the memories.
5. Include timestamps when referencing memories.
6. When referencing images, say "In the stored photo, ..."
7. When referencing audio, say "From your audio note, ..."
8. When referencing videos, say "In the video capture, ..."
9. Pay special attention to "People:" tags - these are the names of people in the memory.
10. Pay special attention to "Location:" information - these are the places where memories occurred.

User Query:
{query}

Retrieved Memories:
{memory_context}

IMPORTANT: Answer ONLY based on the memories above. If the memories don't answer the question, clearly state that you don't have that information in the stored memories.
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are LifeLens, a memory assistant that ONLY answers based on provided memories. You never use external knowledge."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.3,  # Lower temperature for more deterministic, grounded responses
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        return f"Error generating answer: {str(e)}"
