from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.models import global_models as models
from app.schemas import global_schemas as schemas
from app.core import database, auth

router = APIRouter(prefix="/empresas", tags=["Gestión de Empresas (SaaS)"])

@router.post("/", response_model=schemas.EmpresaOut, status_code=status.HTTP_201_CREATED)
def registrar_empresa(
    empresa_in: schemas.EmpresaCreate,
    db: Session = Depends(database.get_db),
    # Descomentar para asegurar que solo Super Admin global puede crearlas
    # current_user: models.Usuario = Depends(auth.check_permissions(["super_admin_global"]))
):
    """
    Endpoint CRÍTICO: Registra una nueva empresa y clona automáticamente su esquema de base de datos.
    """
    if db.query(models.Empresa).filter(models.Empresa.nombre == empresa_in.nombre).first():
        raise HTTPException(status_code=400, detail="El nombre de la empresa ya existe")
        
    if db.query(models.Empresa).filter(models.Empresa.slug == empresa_in.slug).first():
        raise HTTPException(status_code=400, detail="El slug de la empresa ya está en uso")

    schema_name = f"tenant_{empresa_in.slug.replace('-', '_')}"

    nueva_empresa = models.Empresa(
        nombre=empresa_in.nombre,
        slug=empresa_in.slug,
        schema_name=schema_name,
        suscripcion_id=empresa_in.suscripcion_id,
        esta_activa=True
    )
    
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    
    # ¡LA MAGIA MULTI-TENANT FÍSICA!
    # Ejecutar la función PostgreSQL para crear el esquema dinámico
    try:
        db.execute(text(f"SELECT create_tenant_schema('{schema_name}')"))
        db.commit()
        
        # Crear el usuario administrador de la empresa
        admin_usuario = models.Usuario(
            empresa_id=nueva_empresa.id,
            nombre=empresa_in.admin_nombre,
            email=empresa_in.admin_email,
            password_hash=auth.get_password_hash(empresa_in.admin_password),
            rol='admin_empresa',
            esta_activo=True
        )
        db.add(admin_usuario)
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error crítico creando esquema físico: {str(e)}")

    return nueva_empresa

@router.get("/", response_model=List[schemas.EmpresaWithSuscripcionOut])
def listar_empresas(db: Session = Depends(database.get_db)):
    """Lista todas las empresas registradas (Módulo SuperAdmin)."""
    return db.query(models.Empresa).all()
