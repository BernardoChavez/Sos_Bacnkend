import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def patch_permisos_table():
    # Obtener URL de la DB desde el .env
    db_url = os.getenv("DATABASE_URL")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("🔧 Iniciando parche de la tabla 'permisos'...")
        
        # Añadir columnas si no existen
        cur.execute("ALTER TABLE permisos ADD COLUMN IF NOT EXISTS modulo VARCHAR(100);")
        cur.execute("ALTER TABLE permisos ADD COLUMN IF NOT EXISTS caso_uso VARCHAR(100);")
        cur.execute("ALTER TABLE permisos ADD COLUMN IF NOT EXISTS accion VARCHAR(50);")
        
        # Aumentar tamaño de 'codigo' por si acaso
        cur.execute("ALTER TABLE permisos ALTER COLUMN codigo TYPE VARCHAR(100);")
        
        conn.commit()
        print("✅ Columnas añadidas exitosamente.")
        
    except Exception as e:
        print(f"❌ Error al parchear la DB: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    patch_permisos_table()
