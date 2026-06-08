from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.global_models import Empresa

def main():
    db = SessionLocal()
    empresas = db.query(Empresa).filter(Empresa.esta_activa == True).all()
    
    with engine.connect() as conn:
        for empresa in empresas:
            schema = empresa.schema_name
            if schema:
                try:
                    conn.execute(text(f"ALTER TABLE {schema}.bitacora_estados ADD COLUMN latitud_registro FLOAT;"))
                except Exception as e:
                    print(f"Schema {schema} error (latitud): {e}")
                    
                try:
                    conn.execute(text(f"ALTER TABLE {schema}.bitacora_estados ADD COLUMN longitud_registro FLOAT;"))
                except Exception as e:
                    print(f"Schema {schema} error (longitud): {e}")
                
        conn.commit()
    db.close()
    print("Migración de bitacora_estados completada.")

if __name__ == '__main__':
    main()
