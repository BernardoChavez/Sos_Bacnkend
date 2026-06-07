from fastapi import Request
from sqlalchemy.orm import Session
from app.models import global_models as models
from datetime import datetime

def registrar_auditoria(request, user_id, accion, detalle):
    # Evitar registrar el tracking GPS (CU25) para no saturar la base de datos
    if "/tecnicos/perfil/ubicacion" in request.url.path:
        return

    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        nueva_auditoria = models.Auditoria(
            usuario_id=user_id,
            accion=accion,
            detalle=detalle,
            ip=request.client.host if request.client else "127.0.0.1",
            fecha=datetime.utcnow(),
            hora_inicio=datetime.utcnow(),
            hora_cierre=None
        )
        db.add(nueva_auditoria)
        
        # Cerrar sesión anterior para mantener KPIs limpios
        registro_anterior = db.query(models.Auditoria).filter(
            models.Auditoria.usuario_id == user_id,
            models.Auditoria.hora_cierre == None
        ).order_by(models.Auditoria.id.desc()).first()
        
        if registro_anterior:
            registro_anterior.hora_cierre = datetime.utcnow()
            
        db.commit()

    except Exception as e:
        print(f"!!! ERROR CRITICO AUDITORIA (User ID: {user_id}): {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close() # Ahora sí, pero asegurándonos de que es una sesión propia del logger
