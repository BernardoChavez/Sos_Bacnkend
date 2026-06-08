import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No hay GEMINI_API_KEY en tu .env")
else:
    genai.configure(api_key=api_key)
    print("Modelos disponibles con tu API Key:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")
