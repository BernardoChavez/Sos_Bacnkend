from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models import models
from app.schemas import schemas
from app.core import auth, database

router = APIRouter(prefix="/permisos", tags=["Roles y Permisos"])

@router.get("/matriz")
def ver_matriz_permisos(db: Session = Depends(database.get_db), 
                        admin=Depends(auth.check_permissions(["super_admin"]))):
    """Devuelve todos los roles y qué permisos tienen asignados."""
    permisos = db.query(models.Permiso).all()
    roles = ["cliente", "admin_taller", "tecnico", "super_admin"]
    
    matriz = []
    for p in permisos:
        item = {
            "id": p.id, 
            "codigo": p.codigo, 
            "modulo": p.modulo,
            "caso_uso": p.caso_uso,
            "accion": p.accion,
            "descripcion": p.descripcion
        }
        for r in roles:
            tiene = db.query(models.RolPermiso).filter_by(rol=r, permiso_id=p.id).first()
            item[r] = True if tiene else False
        matriz.append(item)
    return matriz

@router.post("/sincronizar")
def toggle_permiso(rol: str, permiso_id: int, db: Session = Depends(database.get_db), 
                   admin=Depends(auth.check_permissions(["super_admin"]))):
    """Activa o desactiva un permiso para un rol de forma segura."""
    # Buscar si ya existe la asociación
    relacion = db.query(models.RolPermiso).filter(
        models.RolPermiso.rol == rol,
        models.RolPermiso.permiso_id == permiso_id
    ).first()

    if relacion:
        db.delete(relacion)
        db.commit()
        return {"status": "removido", "rol": rol, "permiso_id": permiso_id}
    else:
        nueva_relacion = models.RolPermiso(rol=rol, permiso_id=permiso_id)
        db.add(nueva_relacion)
        db.commit()
        return {"status": "asignado", "rol": rol, "permiso_id": permiso_id}
