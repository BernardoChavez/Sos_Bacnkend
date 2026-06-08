from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT email FROM public.usuarios WHERE rol = 'super_admin'")).fetchall()
    for row in result:
        print(row)
