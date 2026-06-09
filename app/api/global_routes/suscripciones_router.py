from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.models import global_models as models
from app.schemas import global_schemas as schemas
from app.core import database, auth

router = APIRouter(prefix="/suscripciones", tags=["Gestión de Suscripciones (SaaS)"])

@router.get("/", response_model=List[schemas.SuscripcionOut])
def listar_suscripciones(db: Session = Depends(database.get_db),
                         current_user: models.Usuario = Depends(auth.check_permissions(["super_admin_global"]))):
    """Lista todas las suscripciones disponibles (solo SuperAdmin)."""
    return db.query(models.Suscripcion).all()

@router.post("/", response_model=schemas.SuscripcionOut, status_code=status.HTTP_201_CREATED)
def crear_suscripcion(suscripcion_in: schemas.SuscripcionCreate, 
                      db: Session = Depends(database.get_db),
                      current_user: models.Usuario = Depends(auth.check_permissions(["super_admin_global"]))):
    """Crea un nuevo plan de suscripción."""
    nueva_suscripcion = models.Suscripcion(**suscripcion_in.model_dump())
    db.add(nueva_suscripcion)
    db.commit()
    db.refresh(nueva_suscripcion)
    return nueva_suscripcion

@router.put("/{suscripcion_id}", response_model=schemas.SuscripcionOut)
def actualizar_suscripcion(suscripcion_id: int, suscripcion_in: schemas.SuscripcionUpdate,
                           db: Session = Depends(database.get_db),
                           current_user: models.Usuario = Depends(auth.check_permissions(["super_admin_global"]))):
    """Actualiza los datos de un plan de suscripción existente."""
    suscripcion = db.query(models.Suscripcion).filter(models.Suscripcion.id == suscripcion_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    
    update_data = suscripcion_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(suscripcion, key, value)
        
    db.commit()
    db.refresh(suscripcion)
    return suscripcion

@router.delete("/{suscripcion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_suscripcion(suscripcion_id: int, 
                         db: Session = Depends(database.get_db),
                         current_user: models.Usuario = Depends(auth.check_permissions(["super_admin_global"]))):
    """Elimina un plan de suscripción si no está en uso."""
    suscripcion = db.query(models.Suscripcion).filter(models.Suscripcion.id == suscripcion_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
        
    # Validar que no haya empresas usando este plan
    empresas_vinculadas = db.query(models.Empresa).filter(models.Empresa.suscripcion_id == suscripcion_id).count()
    if empresas_vinculadas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"No se puede eliminar el plan. Hay {empresas_vinculadas} empresa(s) usándolo actualmente."
        )
        
    db.delete(suscripcion)
    db.commit()
    return None
