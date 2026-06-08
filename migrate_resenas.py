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
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {schema}.resenas (
                            id SERIAL PRIMARY KEY,
                            incidente_id UUID REFERENCES {schema}.incidentes(id) ON DELETE CASCADE UNIQUE,
                            calificacion INTEGER NOT NULL,
                            comentario TEXT,
                            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                except Exception as e:
                    print(f"Schema {schema} error: {e}")
                
        conn.commit()
    db.close()
    print("Migración de resenas completada.")

if __name__ == '__main__':
    main()
