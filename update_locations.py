import os
import random
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

# Lista de coordenadas específicas y dispersas en Santa Cruz de la Sierra
ubicaciones_scz = [
    {"lat": -17.78629, "lon": -63.18117, "zona": "Centro / Plaza 24 de Septiembre"},
    {"lat": -17.75132, "lon": -63.18195, "zona": "Equipetrol / Ventura Mall"},
    {"lat": -17.80155, "lon": -63.17066, "zona": "Plan 3000 / La Campana"},
    {"lat": -17.79589, "lon": -63.15024, "zona": "Villa 1ro de Mayo"},
    {"lat": -17.76510, "lon": -63.13401, "zona": "Parque Industrial"},
    {"lat": -17.74411, "lon": -63.16622, "zona": "Av. Banzer y 4to Anillo"},
    {"lat": -17.81099, "lon": -63.19323, "zona": "Doble Vía La Guardia (4to Anillo)"},
    {"lat": -17.77255, "lon": -63.19502, "zona": "Urubó / Puente"}
]

horarios_ejemplos = [
    {
        "Lunes-Viernes": "08:00 - 18:00",
        "Sabado": "08:00 - 14:00",
        "Domingo": "Cerrado",
        "Emergencias 24/7": True
    },
    {
        "Lunes-Domingo": "24 Horas",
        "Emergencias 24/7": True
    },
    {
        "Lunes-Sabado": "07:00 - 19:00",
        "Domingo": "Solo emergencias de 08:00 a 12:00",
        "Emergencias 24/7": False
    }
]

def update_locations():
    # Evitar asignar la misma ubicación exacta dos veces seguidas si hay varios talleres
    ub_idx = 0 
    
    with engine.connect() as conn:
        schemas = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'")).fetchall()
        
        for schema_row in schemas:
            schema_name = schema_row[0]
            print(f"Actualizando talleres en el esquema: {schema_name}")
            
            conn.execute(text(f"SET search_path TO {schema_name}"))
            talleres = conn.execute(text("SELECT id, nombre FROM talleres")).fetchall()
            
            for t in talleres:
                taller_id = t[0]
                taller_nombre = t[1]
                
                ub = ubicaciones_scz[ub_idx % len(ubicaciones_scz)]
                horario = random.choice(horarios_ejemplos)
                
                # Le damos un pequeñísimo offset al azar para que no estén exactamente en el mismo pixel si se repiten
                lat = ub["lat"] + random.uniform(-0.002, 0.002)
                lon = ub["lon"] + random.uniform(-0.002, 0.002)
                
                conn.execute(
                    text("UPDATE talleres SET latitud = :lat, longitud = :lon, horarios_atencion = :horarios WHERE id = :id"),
                    {
                        "lat": lat, 
                        "lon": lon, 
                        "horarios": json.dumps(horario),
                        "id": taller_id
                    }
                )
                print(f"  -> Taller {taller_nombre} ({taller_id}) | Zona: {ub['zona']} | Horario Asignado")
                ub_idx += 1
                
        conn.commit()
        print("¡Datos (Ubicaciones y Horarios) actualizados exitosamente!")

if __name__ == "__main__":
    update_locations()
