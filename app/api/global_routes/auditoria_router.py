from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import global_models
from app.core import database, auth
from datetime import datetime

router = APIRouter(prefix="/trazabilidad", tags=["Auditoria y Bitacora"])

@router.get("/auditoria")
def obtener_registros_auditoria(db: Session = Depends(database.get_db),
                                current_user: global_models.Usuario = Depends(auth.get_current_user)):
    """Obtiene los registros de auditoría respetando los roles y empresa del usuario."""
    
    if current_user.rol == 'super_admin':
        # El super_admin ve todos los registros de todos los usuarios
        registros_db = db.query(global_models.Auditoria).order_by(desc(global_models.Auditoria.id)).limit(200).all()
        
    elif current_user.rol == 'admin_empresa':
        # El admin_empresa solo ve los registros de los usuarios que pertenecen a SU misma empresa
        registros_db = (db.query(global_models.Auditoria)
                        .join(global_models.Usuario)
                        .filter(global_models.Usuario.empresa_id == current_user.empresa_id)
                        .order_by(desc(global_models.Auditoria.id))
                        .limit(200).all())
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver la bitácora del sistema.")
        
    # Formatear la respuesta para el frontend
    logs_formateados = []
    for reg in registros_db:
        # Asegurar formato seguro en caso de registros huérfanos
        nombre_usuario = reg.usuario.nombre if reg.usuario else "Usuario Desconocido"
        
        # Formatear las fechas si existen
        fecha_str = reg.fecha.strftime("%d/%m/%Y") if reg.fecha else "—"
        inicio_str = reg.hora_inicio.strftime("%I:%M %p") if reg.hora_inicio else "—"
        cierre_str = reg.hora_cierre.strftime("%I:%M %p") if reg.hora_cierre else "Sesión Activa"
        
        logs_formateados.append({
            "id": reg.id,
            "nombre": nombre_usuario,
            "accion": reg.accion,
            "detalle": reg.detalle,
            "ip": reg.ip or "127.0.0.1",
            "fecha": fecha_str,
            "inicio": inicio_str,
            "cierre": cierre_str
        })
        
    return logs_formateados

@router.post("/auditoria/cerrar")
def cerrar_sesion_auditoria(db: Session = Depends(database.get_db),
                            current_user: global_models.Usuario = Depends(auth.get_current_user)):
    """Cierra manualmente el último registro de auditoría activo de un usuario"""
    registro = db.query(global_models.Auditoria).filter(
        global_models.Auditoria.usuario_id == current_user.id,
        global_models.Auditoria.hora_cierre == None
    ).order_by(desc(global_models.Auditoria.id)).first()
    
    if registro:
        registro.hora_cierre = datetime.utcnow()
        db.commit()
    return {"message": "Hito cerrado"}
