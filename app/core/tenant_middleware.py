from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.global_models import Usuario, Empresa

def get_db_for_tenant(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
) -> Session:
    """
    Dependencia de FastAPI (Middleware) para la arquitectura Multi-Tenant Física.
    
    1. Lee el token del usuario actual.
    2. Verifica a qué empresa pertenece el usuario.
    3. Cambia el 'search_path' de PostgreSQL para que todas las consultas
       automáticamente apunten al esquema de esa empresa.
    """
    
    # 1. Si el usuario es un Super Admin Global, puede que queramos pasar el tenant_id por header.
    # Pero por ahora, asumimos que debe tener una empresa asociada, o si es global, opera en public.
    if not current_user.empresa_id:
        # Clientes globales que no pertenecen a ninguna empresa.
        # Solo pueden ver esquemas públicos.
        db.execute(text("SET search_path TO public"))
        return db

    # 2. Obtener la información de la empresa
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    
    if not empresa:
        raise HTTPException(status_code=400, detail="El usuario pertenece a una empresa que ya no existe.")
        
    if not empresa.esta_activa:
        raise HTTPException(status_code=403, detail="La empresa de este taller se encuentra inactiva o suspendida.")
        
    if not empresa.schema_name:
        raise HTTPException(status_code=500, detail="Error crítico: La empresa no tiene un esquema físico asignado.")

    # 3. La magia del Multi-Tenant Físico:
    # Le decimos a PostgreSQL: "De aquí en adelante en esta petición, 
    # busca las tablas primero en el esquema de la empresa, y si no están, búscalas en public".
    db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
    
    # IMPORTANTE: Retornamos la MISMA sesión, pero ya "apuntando" al esquema correcto.
    return db
