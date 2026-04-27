from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models import models
from app.schemas import schemas
from app.core import database, auth

router = APIRouter(prefix="/tecnicos", tags=["Personal Técnico"])

@router.get("/", response_model=List[schemas.UserWithTallerOut])
def listar_todos_los_tecnicos(db: Session = Depends(database.get_db), 
                             current_user=Depends(auth.check_permissions("usuarios.gestionar"))):
    """Lista todos los usuarios con rol técnico (Solo Super Admin)."""
    results = db.query(models.Usuario, models.Taller.nombre, models.Tecnico.disponible)\
              .outerjoin(models.Taller, models.Usuario.taller_id == models.Taller.id)\
              .outerjoin(models.Tecnico, models.Usuario.id == models.Tecnico.usuario_id)\
              .filter(models.Usuario.rol == "tecnico").all()
    
    users = []
    for u, taller_nombre, disponible in results:
        # Auto-reparación: Si es técnico pero no tiene ficha, la creamos
        if disponible is None:
            nueva_ficha = models.Tecnico(usuario_id=u.id, taller_id=u.taller_id, disponible=True)
            db.add(nueva_ficha)
            db.commit()
            disponible = True
            
        users.append({
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "telefono": u.telefono,
            "rol": u.rol,
            "taller_id": u.taller_id,
            "taller_nombre": taller_nombre if taller_nombre else "Independiente",
            "disponible": disponible
        })
    return users

@router.post("/")
def registrar_tecnico(tecnico: schemas.TecnicoCreate, db: Session = Depends(database.get_db)):
    db_existe = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == tecnico.usuario_id).first()
    if db_existe:
        raise HTTPException(status_code=400, detail="El técnico ya tiene una ficha activa")

    nuevo_tecnico = models.Tecnico(
        usuario_id=tecnico.usuario_id,
        taller_id=tecnico.taller_id,
        especialidad_principal=tecnico.especialidad_principal,
        disponible=True
    )
    db.add(nuevo_tecnico)
    db.commit()
    return {"message": "Técnico vinculado exitosamente"}

@router.get("/perfil", response_model=schemas.TecnicoOut)
def obtener_perfil_tecnico(db: Session = Depends(database.get_db), 
                           current_user: models.Usuario = Depends(auth.check_permissions("tecnico.operar"))):
    """Obtiene la ficha técnica del usuario logueado."""
    tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="No se encontró tu ficha técnica. Contacta al admin.")
    return tecnico

@router.put("/perfil", response_model=schemas.TecnicoOut)
def actualizar_perfil_tecnico(data: schemas.TecnicoUpdate, 
                              db: Session = Depends(database.get_db), 
                              current_user: models.Usuario = Depends(auth.check_permissions("tecnico.operar"))):
    """Permite al técnico actualizar su propia disponibilidad y especialidad."""
    tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Ficha técnica no encontrada")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tecnico, key, value)
    
    db.commit()
    db.refresh(tecnico)
    return tecnico

@router.patch("/{usuario_id}/disponibilidad")
def cambiar_disponibilidad(usuario_id: int, disponible: bool, db: Session = Depends(database.get_db)):
    tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == usuario_id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="No se encontró la ficha del técnico")
    
    tecnico.disponible = disponible
    db.commit()
    return {"status": "success", "nueva_disponibilidad": tecnico.disponible}

@router.patch("/perfil/ubicacion")
def actualizar_ubicacion(latitud: float, longitud: float, 
                        db: Session = Depends(database.get_db), 
                        current_user: models.Usuario = Depends(auth.check_permissions("tecnico.operar"))):
    """CU24: Actualiza la geolocalización en tiempo real del técnico."""
    tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Ficha técnica no encontrada")
    
    tecnico.latitud = latitud
    tecnico.longitud = longitud
    db.commit()
    return {"status": "success", "latitud": latitud, "longitud": longitud}
