from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import models
from app.schemas import schemas
from app.core import auth, database

router = APIRouter(prefix="/especialidades", tags=["Catálogo de Especialidades"])

@router.post("/", response_model=schemas.EspecialidadOut, status_code=status.HTTP_201_CREATED)
def crear_especialidad(
    especialidad: schemas.EspecialidadCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin"]))
):
    nueva_esp = models.Especialidad(**especialidad.model_dump())
    db.add(nueva_esp)
    db.commit()
    db.refresh(nueva_esp)
    return nueva_esp

@router.get("/", response_model=List[schemas.EspecialidadOut])
def listar_especialidades(
    db: Session = Depends(database.get_db)
):
    return db.query(models.Especialidad).all()

# Endpoint para asociar especialidad a taller
@router.post("/taller/{taller_id}/asignar/{especialidad_id}", status_code=status.HTTP_201_CREATED)
def asignar_especialidad_taller(
    taller_id: int,
    especialidad_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_taller"]))
):
    if current_user.rol == "admin_taller" and current_user.taller_id != taller_id:
        raise HTTPException(status_code=403, detail="No puedes asignar especialidades a un taller que no es tuyo")

    taller = db.query(models.Taller).filter(models.Taller.id == taller_id).first()
    especialidad = db.query(models.Especialidad).filter(models.Especialidad.id == especialidad_id).first()
    
    if not taller or not especialidad:
        raise HTTPException(status_code=404, detail="Taller o Especialidad no encontrados")

    # Verificamos si ya existe
    existe = db.query(models.TallerEspecialidad).filter_by(taller_id=taller_id, especialidad_id=especialidad_id).first()
    if existe:
        raise HTTPException(status_code=400, detail="El taller ya tiene esta especialidad asignada")

    nueva_asignacion = models.TallerEspecialidad(taller_id=taller_id, especialidad_id=especialidad_id)
    db.add(nueva_asignacion)
    db.commit()
    return {"message": "Especialidad asignada correctamente al taller"}

@router.put("/{id}", response_model=schemas.EspecialidadOut)
def actualizar_especialidad(
    id: int, 
    esp_update: schemas.EspecialidadCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin"]))
):
    esp_db = db.query(models.Especialidad).filter(models.Especialidad.id == id).first()
    if not esp_db:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada")
    
    esp_db.nombre_especialidad = esp_update.nombre_especialidad
    db.commit()
    db.refresh(esp_db)
    return esp_db

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_especialidad(
    id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin"]))
):
    esp_db = db.query(models.Especialidad).filter(models.Especialidad.id == id).first()
    if not esp_db:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada")
    db.delete(esp_db)
    db.commit()
    return None

@router.delete("/taller/{taller_id}/quitar/{especialidad_id}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_especialidad_taller(
    taller_id: int,
    especialidad_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_taller"]))
):
    if current_user.rol == "admin_taller" and current_user.taller_id != taller_id:
        raise HTTPException(status_code=403, detail="No puedes modificar especialidades de otro taller")

    asignacion = db.query(models.TallerEspecialidad).filter_by(taller_id=taller_id, especialidad_id=especialidad_id).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="El taller no tiene esta especialidad asignada")
        
    db.delete(asignacion)
    db.commit()
    return None
