from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import tenant_models as models
from app.schemas import tenant_schemas as schemas
from app.core import auth, database, tenant_middleware

router = APIRouter(prefix="/talleres", tags=["Gestión de Talleres"])

@router.post("/", response_model=schemas.TallerOut)
def crear_taller(taller: schemas.TallerCreate, db: Session = Depends(tenant_middleware.get_db_for_tenant), 
                 current_user=Depends(auth.check_permissions("talleres.registrar"))):
    
    if not current_user.empresa:
        raise HTTPException(status_code=403, detail="No perteneces a ninguna empresa.")
        
    suscripcion = current_user.empresa.suscripcion
    if not suscripcion:
        raise HTTPException(status_code=403, detail="Tu empresa no tiene un plan de suscripción activo.")
        
    max_talleres = suscripcion.max_talleres
    talleres_actuales = db.query(models.Taller).count()
    
    if talleres_actuales >= max_talleres:
        raise HTTPException(
            status_code=402, 
            detail=f"Has alcanzado el límite de {max_talleres} talleres de tu plan. Actualiza tu suscripción."
        )

    nuevo = models.Taller(**taller.model_dump())
    db.add(nuevo)
    db.commit()
    
    # Después del commit, la conexión puede reiniciarse. Restauramos el search_path.
    from sqlalchemy import text
    db.execute(text(f"SET search_path TO {current_user.empresa.schema_name}, public"))
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=List[schemas.TallerWithAdminOut])
def listar_talleres(db: Session = Depends(tenant_middleware.get_db_for_tenant)):
    """Lista todos los talleres (sucursales)."""
    talleres = db.query(models.Taller).all()
    
    result = []
    for taller in talleres:
        taller_dict = schemas.TallerWithAdminOut.model_validate(taller)
        taller_dict.admin_nombre = "Admin. de Empresa" # En el futuro se mapeará con admin_taller
        result.append(taller_dict)
        
    return result


@router.get("/{id}", response_model=schemas.TallerOut)
def obtener_taller(id: int, db: Session = Depends(tenant_middleware.get_db_for_tenant)):
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return taller

@router.patch("/{id}/configuracion")
def configurar_taller_cu8(id: int, config: schemas.TallerUpdate, 
                         db: Session = Depends(tenant_middleware.get_db_for_tenant),
                         current_user=Depends(auth.get_current_user)):
    """CU8: Definir horarios y zonas de cobertura geográfica."""
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller: raise HTTPException(status_code=404)
    
    # Solo el dueño o SuperAdmin o AdminEmpresa o AdminTaller
    if current_user.rol not in ["super_admin", "admin_empresa", "admin_taller"]:
        raise HTTPException(status_code=403, detail="No autorizado")
        
    if current_user.rol == "admin_taller" and current_user.taller_id != id:
        raise HTTPException(status_code=403, detail="No puedes configurar un taller distinto al tuyo")

    if config.horarios_atencion: taller.horarios_atencion = config.horarios_atencion
    
    db.commit()
    return {"message": "Configuración de cobertura y horarios actualizada"}

@router.put("/{id}", response_model=schemas.TallerOut)
def actualizar_taller(id: int, taller_in: schemas.TallerUpdate, db: Session = Depends(tenant_middleware.get_db_for_tenant),
                      current_user=Depends(auth.get_current_user)):
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller: raise HTTPException(status_code=404, detail="Taller no encontrado")

    # Seguridad: SuperAdmin, AdminEmpresa, y AdminTaller (si es su propio taller)
    if current_user.rol not in ["super_admin", "admin_empresa", "admin_taller"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar talleres")
        
    if current_user.rol == "admin_taller" and current_user.taller_id != id:
        raise HTTPException(status_code=403, detail="No puedes editar un taller distinto al tuyo")
    
    update_data = taller_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(taller, key, value)
        
    # Forzar la actualización del campo JSON en SQLAlchemy
    if "horarios_atencion" in update_data:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(taller, "horarios_atencion")
    
    db.commit()
    from sqlalchemy import text
    db.execute(text(f"SET search_path TO {current_user.empresa.schema_name}, public"))
    db.refresh(taller)
    return taller

@router.delete("/{id}")
def eliminar_taller(id: int, db: Session = Depends(tenant_middleware.get_db_for_tenant),
                    current_user=Depends(auth.check_permissions("talleres.registrar"))):
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller: raise HTTPException(status_code=404, detail="Taller no encontrado")
    
    db.delete(taller)
    db.commit()
    return {"message": "Taller eliminado exitosamente"}
