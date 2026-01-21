def process_text(text_content):
    """
    Process raw text input.
    """
    if not text_content or not text_content.strip():
        raise ValueError("Text content cannot be empty.")
        
    return {
        "content": text_content.strip()
    }
