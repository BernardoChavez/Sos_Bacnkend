import os
from sqlalchemy import text
from app.core.database import engine

def apply_schema():
    print("Aplicando supabase_schema.sql...")
    with open('supabase_schema.sql', 'r', encoding='utf-8') as f:
        sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(sql))
    
    print("¡Base de datos actualizada con éxito!")

if __name__ == "__main__":
    apply_schema()
