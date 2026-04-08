import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')

import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY
from PIL import Image
import io
import base64
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    # Handle missing key gracefully or log warning
    pass

def process_image(image_file, enable_quality_check=True, patient_context=None):
    """
    Process an uploaded image with optional quality checking and retry logic.
    
    Args:
        image_file: Uploaded image file
        enable_quality_check: Whether to use quality critic agent (default: True)
        patient_context: Optional patient context for ingestion planning
    
    Returns:
        Dictionary with caption, base64, quality_score, retry_count
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Convert to PIL Image
    image = Image.open(image_file)
    
    # Ingestion Planning (optional)
    file_size = len(image_file.getvalue()) if hasattr(image_file, 'getvalue') else 0
    ingestion_plan = None
    
    if patient_context:
        try:
            from lifelens.agents import plan_ingestion_strategy
            ingestion_plan = plan_ingestion_strategy(
                file_type="image",
                file_name=getattr(image_file, 'name', 'unknown.jpg'),
                file_size=file_size,
                patient_context=patient_context
            )
            logger.info(f"Ingestion strategy: {ingestion_plan['strategy']}")
        except Exception as e:
            logger.warning(f"Ingestion planning failed: {e}")
    
    # Determine caption depth
    depth = "detailed" if not ingestion_plan or ingestion_plan.get("caption_depth") == "detailed" else "basic"
    
    # Generate Caption with Person Identification
    max_retries = 2
    retry_count = 0
    best_caption = None
    best_quality = 0
    
    while retry_count <= max_retries:
        model = genai.GenerativeModel('gemini-flash-latest')
        
        if depth == "detailed":
            prompt = """Describe this image in detail for a blind person. 
            If there are people in the photo, identify them by their apparent relationship or role (e.g., 'a young woman', 'an elderly man', 'a child').
            If you can infer names from context clues in the image (text, name tags, etc.), mention them.
            Be warm and descriptive. Include emotional context and environmental details.
            
            IMPORTANT: If this is a screenshot, document, or contains any visible text (app names, titles, labels, etc.), 
            extract and include ALL visible text in your description. This is crucial for search and retrieval."""
        else:
            prompt = """Describe this image briefly. Mention any people, objects, and the general scene.
            If this is a screenshot or contains visible text, extract and include the key text."""
        
        response = model.generate_content([prompt, image])
        caption = response.text
        
        # Extract visible text for screenshots/documents (additional pass for better accuracy)
        extracted_text = ""
        try:
            text_extraction_prompt = """Extract ALL visible text from this image. 
            Include app names, titles, headings, labels, menu items, and any other readable text.
            Format as a comma-separated list of key terms and phrases.
            If no text is visible, respond with 'NO_TEXT'."""
            
            text_response = model.generate_content([text_extraction_prompt, image])
            extracted_text = text_response.text.strip()
            
            # Append extracted text to caption if meaningful text was found
            if extracted_text and extracted_text != "NO_TEXT" and len(extracted_text) > 5:
                caption = f"{caption}\n\n[Visible text in image: {extracted_text}]"
                logger.info(f"Extracted visible text: {extracted_text[:100]}...")
        except Exception as e:
            logger.warning(f"Text extraction pass failed: {e}")
        
        # Quality Check
        if enable_quality_check:
            try:
                from lifelens.agents import critique_caption_quality, should_retry_processing
                critique = critique_caption_quality(caption, "image")
                
                logger.info(f"Caption quality: {critique['quality_score']}/10 (attempt {retry_count + 1})")
                
                # Track best result
                if critique['quality_score'] > best_quality:
                    best_quality = critique['quality_score']
                    best_caption = caption
                
                # Decide if retry is needed
                if should_retry_processing(critique, retry_count):
                    logger.info(f"Retrying caption generation: {critique['reasoning']}")
                    retry_count += 1
                    continue
                else:
                    # Accept this result
                    break
                    
            except Exception as e:
                logger.warning(f"Quality check failed: {e}")
                best_caption = caption
                break
        else:
            best_caption = caption
            break
    
    # Use best caption found
    final_caption = best_caption if best_caption else caption
    
    # Convert to Base64
    buffered = io.BytesIO()
    image.save(buffered, format=image.format or "JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    result = {
        "caption": final_caption,
        "base64": img_str,
        "quality_score": best_quality if enable_quality_check else None,
        "retry_count": retry_count
    }
    
    # Check if follow-up trigger needed
    if ingestion_plan:
        try:
            from lifelens.agents import should_trigger_follow_up
            trigger_check = should_trigger_follow_up(result, ingestion_plan)
            if trigger_check.get("trigger_needed"):
                result["follow_up_trigger"] = trigger_check
                logger.info(f"Follow-up needed: {trigger_check['message']}")
        except Exception as e:
            logger.warning(f"Follow-up trigger check failed: {e}")
    
    return result
