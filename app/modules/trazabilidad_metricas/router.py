from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core import database, auth
from app.models import models
from datetime import datetime
from uuid import UUID
from app.core.socket_manager import manager

router = APIRouter(prefix="/trazabilidad", tags=["Trazabilidad y Auditoría"])

@router.post("/bitacora/{incidente_id}")
def registrar_hito(incidente_id: UUID, estado_nuevo: str, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db), 
                   current_user: models.Usuario = Depends(auth.get_current_user)):
    """CU2.2.14: Registro de estados y trazabilidad."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    estado_anterior = incidente.estado
    incidente.estado = estado_nuevo
    
    nueva_bitacora = models.BitacoraEstado(
        incidente_id=incidente_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_cambio_id=current_user.id
    )
    db.add(nueva_bitacora)
    db.commit()

    estado_texto = "en camino" if estado_nuevo == "en_camino" else estado_nuevo.replace('_', ' ')
    titulo_notif = "Actualización de Servicio"
    mensaje_notif = f"Tu servicio ha cambiado a estado: {estado_texto}."

    # 1. Guardar notificación persistente en BD
    nueva_notif = models.Notificacion(
        usuario_id=incidente.cliente_id,
        titulo=titulo_notif,
        mensaje=mensaje_notif
    )
    db.add(nueva_notif)
    db.commit()

    # 2. Enviar alerta en tiempo real (Socket)
    background_tasks.add_task(
        manager.send_personal_message,
        {
            "tipo": "notificacion",
            "titulo": titulo_notif,
            "mensaje": mensaje_notif,
            "fecha": datetime.utcnow().strftime("%H:%M")
        },
        incidente.cliente_id
    )

    return {"status": "success", "nuevo_estado": estado_nuevo}

@router.get("/auditoria")
def obtener_auditoria(db: Session = Depends(database.get_db), 
                      current_user: models.Usuario = Depends(auth.check_permissions("sistema.auditoria.ver"))):
    """CU2.2.14: Auditoría del sistema."""
    logs = db.query(models.Auditoria).order_by(models.Auditoria.id.desc()).limit(100).all()
    resultado = []
    for log in logs:
        resultado.append({
            "nombre": log.usuario.nombre if log.usuario else "Sistema",
            "accion": log.accion,
            "detalle": log.detalle,
            "ip": log.ip,
            "fecha": log.fecha.strftime("%Y-%m-%d %H:%M:%S"),
            "inicio": log.hora_inicio.strftime("%H:%M:%S") if log.hora_inicio else "N/A",
            "cierre": log.hora_cierre.strftime("%H:%M:%S") if log.hora_cierre else "Sesión Activa"
        })
    return resultado

@router.post("/auditoria/cerrar")
def cerrar_sesion_auditoria(db: Session = Depends(database.get_db), 
                             current_user: models.Usuario = Depends(auth.get_current_user)):
    """CU2.2.14: Cierre de hito de auditoría."""
    registro = db.query(models.Auditoria).filter(
        models.Auditoria.usuario_id == current_user.id,
        models.Auditoria.hora_cierre == None
    ).order_by(models.Auditoria.id.desc()).first()
    
    if registro:
        registro.hora_cierre = datetime.utcnow()
        db.commit()
    
    return {"status": "success"}
