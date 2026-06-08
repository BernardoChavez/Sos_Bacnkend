from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import global_models as models
from app.schemas import global_schemas as schemas
from app.core import auth, database

router = APIRouter(prefix="/vehiculos", tags=["Gestión de Vehículos"])

@router.post("/", response_model=schemas.VehiculoOut, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    vehiculo: schemas.VehiculoCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    # ... resto del código igual ...
    cliente_id = vehiculo.cliente_id
    if current_user.rol == "cliente":
        cliente_id = current_user.id
    elif not cliente_id:
        raise HTTPException(status_code=400, detail="Debe especificar un cliente_id si es admin")

    datos = vehiculo.model_dump(exclude={"cliente_id"})
    nuevo_vehiculo = models.Vehiculo(**datos, cliente_id=cliente_id)
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    return nuevo_vehiculo

@router.get("/", response_model=List[schemas.VehiculoOut])
def listar_vehiculos(
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    query = db.query(models.Vehiculo, models.Usuario.nombre)\
              .outerjoin(models.Usuario, models.Vehiculo.cliente_id == models.Usuario.id)

    if current_user.rol == "cliente":
        results = query.filter(models.Vehiculo.cliente_id == current_user.id).all()
    else:
        results = query.all()
    
    vehiculos = []
    for v, nombre in results:
        vehiculos.append({
            "id": v.id, "placa": v.placa, "marca": v.marca, "modelo": v.modelo,
            "color": v.color, "anio": v.anio, "cliente_id": v.cliente_id,
            "cliente_nombre": nombre if nombre else "Sin Propietario"
        })
    return vehiculos

@router.put("/{id}", response_model=schemas.VehiculoOut)
def actualizar_vehiculo(
    id: int, 
    vehiculo_update: schemas.VehiculoUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    vehiculo_db = db.query(models.Vehiculo).filter(models.Vehiculo.id == id).first()
    if not vehiculo_db:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    if current_user.rol == "cliente" and vehiculo_db.cliente_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes modificar un vehículo que no es tuyo")

    update_data = vehiculo_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vehiculo_db, key, value)
        
    db.commit()
    db.refresh(vehiculo_db)
    return vehiculo_db

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_vehiculo(
    id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    vehiculo = db.query(models.Vehiculo).filter(models.Vehiculo.id == id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        
    if current_user.rol == "cliente" and vehiculo.cliente_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar un vehículo que no es tuyo")
        
    db.delete(vehiculo)
    db.commit()
    return None
