import os
import json
import tempfile
import google.generativeai as genai
from fastapi import UploadFile

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def analizar_emergencia_con_ia(archivos: list[UploadFile], especialidades_permitidas: list[str]) -> dict:
    """
    Recibe una lista de archivos (fotos/audios), los sube a Gemini y devuelve un JSON:
    {
      "especialidad": "Mecanica" | "Chaperio" | "Electricista" | "Gomeria" | "General",
      "gravedad": "Alta" | "Media" | "Baja",
      "resumen": "Descripción del problema..."
    }
    """
    if not api_key:
        return {"especialidad": "General", "gravedad": "Media", "resumen": "Alerta generada sin IA (API Key faltante)."}

    # Utilizamos Gemini 3.5 Flash que soporta procesamiento multimodal rápido
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    uploaded_files = []
    temp_files = []
    
    try:
        # Guardar archivos temporalmente para subirlos a Gemini
        for archivo in archivos:
            if not archivo or not archivo.filename:
                continue
                
            suffix = os.path.splitext(archivo.filename)[1] or ".webm"
            # Crear archivo temporal
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(archivo.file.read())
            temp_file.close()
            temp_files.append(temp_file.name)
            
            # Subir a Gemini File API
            archivo.file.seek(0)
            print(f"Subiendo a Gemini: {temp_file.name}")
            g_file = genai.upload_file(path=temp_file.name)
            
            import time
            # Esperar a que el archivo sea procesado por los servidores de Google
            while g_file.state.name == "PROCESSING":
                print(f"  -> Esperando procesamiento del archivo {g_file.name}...")
                time.sleep(1)
                g_file = genai.get_file(g_file.name)
                
            if g_file.state.name == "FAILED":
                print(f"Error procesando archivo {g_file.name} en Gemini.")
                continue
                
            uploaded_files.append(g_file)
            
        if not uploaded_files:
            return {"especialidad": "General", "gravedad": "Media", "resumen": "No se proporcionaron evidencias."}
            
        prompt = f"""
        Eres un asistente de emergencias automotrices (Triage).
        Escucha el audio y/o mira las fotos proporcionadas por el conductor.
        Identifica exactamente cuál es el problema y responde ÚNICAMENTE con un JSON válido usando el siguiente esquema:
        {{
            "especialidad": "Elige estrictamente una de estas opciones exactas disponibles en la red de talleres: {', '.join(especialidades_permitidas)}",
            "gravedad": "Elige estrictamente una de estas opciones: Alta, Media, Baja",
            "resumen": "Escribe un breve resumen de lo que el cliente relata que le sucedió al auto."
        }}
        NO escribas formato Markdown. Solo devuelve el objeto JSON crudo.
        """
        
        # Enviar petición a Gemini con todos los archivos + texto
        contents = uploaded_files + [prompt]
        response = model.generate_content(contents)
        
        # Limpiar respuesta (a veces Gemini devuelve ```json ... ```)
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.startswith("```"):
            text_resp = text_resp[3:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
            
        text_resp = text_resp.strip()
        
        try:
            return json.loads(text_resp)
        except json.JSONDecodeError:
            print("Error decodificando JSON de Gemini:", text_resp)
            return {"especialidad": "General", "gravedad": "Media", "resumen": text_resp[:200]}
            
    except Exception as e:
        print("Error en Gemini AI:", e)
        return {"especialidad": "General", "gravedad": "Media", "resumen": f"Error procesando IA: {str(e)}"}
        
    finally:
        # Limpiar archivos de Gemini
        for g_file in uploaded_files:
            try:
                genai.delete_file(g_file.name)
            except:
                pass
                
        # Limpiar archivos temporales locales
        for tf in temp_files:
            try:
                if os.path.exists(tf):
                    os.remove(tf)
            except:
                pass
