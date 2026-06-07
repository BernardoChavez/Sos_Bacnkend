import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
print(f"Clave detectada: {API_KEY[:8]}...{API_KEY[-4:] if API_KEY else ''}")

if not API_KEY:
    print("❌ ERROR: GEMINI_API_KEY no encontrada en el .env")
    exit(1)

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Hola, responde con la palabra OK si me escuchas.")
    print(f"✅ Respuesta de Gemini: {response.text.strip()}")
except Exception as e:
    print(f"❌ ERROR AL LLAMAR A GEMINI: {e}")
