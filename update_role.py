from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("UPDATE public.usuarios SET rol = 'super_admin' WHERE rol = 'super_admin_global'"))
    conn.commit()
    print("Rol actualizado a super_admin.")
