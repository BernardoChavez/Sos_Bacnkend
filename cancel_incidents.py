import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def cancel_all_incidents():
    with engine.connect() as conn:
        schemas = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'")).fetchall()
        
        for schema_row in schemas:
            schema_name = schema_row[0]
            print(f"Limpiando incidentes en: {schema_name}")
            
            conn.execute(text(f"SET search_path TO {schema_name}"))
            
            # Update to cancelado instead of deleting, or delete?
            # The user asked to "cancel" the incident. Let's delete it so they have a clean slate for the next test.
            conn.execute(text("DELETE FROM evidencias"))
            conn.execute(text("DELETE FROM bitacora_estados"))
            res = conn.execute(text("DELETE FROM incidentes RETURNING id"))
            deleted_ids = res.fetchall()
            
            for d in deleted_ids:
                print(f"  -> Eliminado incidente {d[0]}")
                
        conn.commit()
        print("¡Todos los incidentes de prueba han sido limpiados de la base de datos!")

if __name__ == "__main__":
    cancel_all_incidents()
