import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY
from PIL import Image
import io
import base64

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    # Handle missing key gracefully or log warning
    pass

def process_image(image_file):
    """
    Process an uploaded image:
    1. Generate a caption using Gemini Flash.
    2. Return the caption and base64 encoded image.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Convert to PIL Image
    image = Image.open(image_file)
    
    # Generate Caption with Person Identification
    model = genai.GenerativeModel('gemini-flash-latest')
    prompt = """Describe this image in detail for a blind person. 
    If there are people in the photo, identify them by their apparent relationship or role (e.g., 'a young woman', 'an elderly man', 'a child').
    If you can infer names from context clues in the image (text, name tags, etc.), mention them.
    Be warm and descriptive."""
    
    response = model.generate_content([prompt, image])
    caption = response.text
    
    # Convert to Base64
    buffered = io.BytesIO()
    image.save(buffered, format=image.format or "JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        "caption": caption,
        "base64": img_str
    }
