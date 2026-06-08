from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core import database, auth
from app.models import global_models
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"]
)

class NotificacionOut(BaseModel):
    id: int
    titulo: str
    mensaje: str
    leido: bool
    fecha: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[NotificacionOut])
def listar_notificaciones(
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    """Obtener todas las notificaciones del usuario logueado."""
    notificaciones = db.query(global_models.Notificacion)\
                       .filter(global_models.Notificacion.usuario_id == current_user.id)\
                       .order_by(global_models.Notificacion.fecha_envio.desc())\
                       .all()
    
    # Mapear para coincidir con la expectativa del frontend (fecha_envio -> fecha)
    res = []
    for n in notificaciones:
        res.append({
            "id": n.id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "leido": n.leido,
            "fecha": n.fecha_envio
        })
    return res

@router.patch("/{id}/leer")
def marcar_notificacion_leida(
    id: int,
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    """Marcar una notificación como leída."""
    notif = db.query(global_models.Notificacion)\
              .filter(global_models.Notificacion.id == id, global_models.Notificacion.usuario_id == current_user.id)\
              .first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    notif.leido = True
    db.commit()
    return {"message": "Marcada como leída"}
