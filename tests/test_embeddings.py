import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env
load_dotenv('lifelens/.env')
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("Error: GEMINI_API_KEY not found in lifelens/.env")
    exit(1)

genai.configure(api_key=api_key)

models_to_try = [
    "models/text-embedding-004",
    "text-embedding-004",
    "models/embedding-001",
    "embedding-001",
    "models/gemini-embedding-001",
    "gemini-embedding-001"
]

for model_name in models_to_try:
    print(f"Trying model: {model_name}...")
    try:
        result = genai.embed_content(
            model=model_name,
            content="Hello world",
            task_type="retrieval_query"
        )
        print(f"SUCCESS with {model_name}! Vector size: {len(result['embedding'])}")
        # If success, we found it
    except Exception as e:
        print(f"FAILED with {model_name}: {e}")

print("\nListing all available models with embedContent support:")
try:
    for m in genai.list_models():
        if 'embedContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
