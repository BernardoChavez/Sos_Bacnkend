import asyncio
import os
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configuración de Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY and API_KEY != "tu_api_key_de_gemini_aqui":
    genai.configure(api_key=API_KEY)
    # Usamos el alias más compatible
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    model = None

async def process_voice_report(audio_file_url: str) -> str:
    """Trascribe el audio real usando Gemini 1.5 Flash (CU2.2.8)."""
    if not model: return "Error: IA no configurada"
    
    try:
        filename = audio_file_url.split('/')[-1]
        file_path = os.path.join("uploads", filename)
        
        if not os.path.exists(file_path):
            return "El usuario reporta un problema desconocido."

        mime_type = "audio/webm" 
        with open(file_path, "rb") as f:
            audio_data = f.read()
            
        response = model.generate_content([
            "Escucha este audio de un conductor en emergencia y transcribe EXACTAMENTE lo que dice.",
            {"mime_type": mime_type, "data": audio_data}
        ])
        return response.text
    except Exception as e:
        print(f"Error Gemini Audio: {e}")
        return "Asistencia solicitada. El usuario requiere apoyo técnico inmediato."

async def classify_incident_vision(image_urls: list[str], context: str = "") -> Dict[str, Any]:
    """Analiza las imágenes REALES con Gemini Vision (CU2.2.9 & 2.2.10)."""
    if not model:
        return {"especialidad": "Mecánica General", "prioridad": "Baja", "resumen": "IA no conectada"}

    try:
        parts = ["Actúa como experto mecánico senior."]
        
        import mimetypes
        for url in image_urls:
            filename = url.split('/')[-1]
            file_path = os.path.join("uploads", filename)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if not mime_type: mime_type = "image/jpeg"
                    parts.append({"mime_type": mime_type, "data": f.read()})

        # Restaurando el Prompt Avanzado Detallado
        parts.append(f"""
            CONTEXTO DEL CONDUCTOR: "{context}"

            INSTRUCCIONES TÉCNICAS:
            Analiza las imágenes y el audio para generar un reporte profesional.
            
            1. CATEGORIZACIÓN:
            - Batería / Eléctrico: Fallas de arranque, luces, cables.
            - Llanta / Suspensión: Pinchazos, ruidos en ruedas, amortiguadores.
            - Choque / Carrocería: Daños externos, vidrios, colisiones.
            - Motor / Mecánica: Humo, pérdida de potencia, ruidos internos, fugas.

            2. ESPECIALIDAD RECOMENDADA:
            "Electricista Automotriz", "Servicio de Neumáticos", "Taller de Colisión", "Mecánica General".

            3. FICHA TÉCNICA ESTRUCTURADA:
            Genera un diagnóstico detallado siguiendo este formato exacto:
            - Problema: [Descripción técnica de lo observado]
            - Causa: [Explicación de por qué ocurrió]
            - Acción: [Pasos para la solución inmediata]

            Responde ÚNICAMENTE en este formato JSON:
            {{
              "categoria": "...",
              "especialidad": "...",
              "prioridad": "Alta | Media | Baja",
              "resumen": "Título corto del problema",
              "diagnostico_ia": "FICHA TÉCNICA ESTRUCTURADA: \\n- Problema: ...\\n- Causa: ...\\n- Acción: ..."
            }}
        """)

        response = model.generate_content(parts)
        
        import json
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
            
        raise Exception("Formato JSON no detectado")
        
    except Exception as e:
        error_msg = str(e)
        print(f"!!! IA FALLBACK: {error_msg}")
        
        # Fallback inteligente basado en palabras clave si la API falla
        categoria = "Otros"
        especialidad = "Mecánica General"
        prioridad = "Media"
        ctx = context.lower()
        if any(w in ctx for w in ["bateria", "batería", "arranca"]):
            categoria, especialidad = "Batería", "Electricista Automotriz"
        elif any(w in ctx for w in ["llanta", "neumatico", "pinchazo"]):
            categoria, especialidad = "Llanta", "Servicio de Neumáticos"
        elif any(w in ctx for w in ["choque", "accidente", "golpe"]):
            categoria, especialidad = "Choque", "Taller de Colisión"
            prioridad = "Alta"

        return {
            "categoria": categoria,
            "especialidad": especialidad,
            "prioridad": prioridad,
            "resumen": f"Asistencia en {categoria}",
            "diagnostico_ia": f"FICHA TÉCNICA ESTRUCTURADA (MODO SEGURO):\n- Problema: Posible falla en {categoria}\n- Causa: Identificada por patrones de voz\n- Acción: Enviar especialista en {especialidad} para inspección."
        }

async def evaluate_priority(context: str) -> str:
    ctx = context.lower()
    if "fuego" in ctx or "choque" in ctx or "sangre" in ctx: return "Alta"
    return "Media"

async def generate_incident_summary(context: str) -> str:
    return f"Resumen: {context[:100]}..."
