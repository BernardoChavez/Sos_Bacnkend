from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models import models
from app.core import database, auth
from datetime import datetime

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

@router.get("/", response_model=List[dict])
def listar_notificaciones(db: Session = Depends(database.get_db), 
                        current_user: models.Usuario = Depends(auth.get_current_user)):
    """CU2.2.13: Lista las notificaciones push (simuladas) del usuario."""
    notifs = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == current_user.id
    ).order_by(models.Notificacion.fecha_envio.desc()).limit(10).all()
    
    return [
        {
            "id": n.id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "leido": n.leido,
            "fecha": n.fecha_envio.strftime("%Y-%m-%d %H:%M")
        } for n in notifs
    ]

@router.patch("/{notif_id}/leer")
def marcar_como_leida(notif_id: int, db: Session = Depends(database.get_db), 
                      current_user: models.Usuario = Depends(auth.get_current_user)):
    notif = db.query(models.Notificacion).filter(
        models.Notificacion.id == notif_id,
        models.Notificacion.usuario_id == current_user.id
    ).first()
    
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    notif.leido = True
    db.commit()
    return {"status": "success"}
