from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core import database, auth
from app.models import models
from datetime import datetime
from uuid import UUID
from app.core.socket_manager import manager

router = APIRouter(prefix="/gestion", tags=["Pagos"])

@router.post("/pagos/{incidente_id}")
def procesar_pago(incidente_id: UUID, metodo: str, monto: float, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    """CU2.2.5: Registro de pagos."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    if metodo == 'EFECTIVO':
        pago_existente = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
        if pago_existente:
            pago_existente.metodo_pago = 'EFECTIVO'
            pago_existente.estado_pago = 'pendiente_confirmacion'
            pago_existente.monto = monto
        else:
            pago = models.Pago(
                incidente_id=incidente_id,
                monto=monto,
                metodo_pago='EFECTIVO',
                estado_pago='pendiente_confirmacion',
                fecha_pago=datetime.utcnow()
            )
            db.add(pago)
        
        incidente.estado = "esperando_confirmacion_pago"
        db.commit()
        return {"status": "pending", "mensaje": "Pago registrado en efectivo."}

    pago = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
    
    if pago:
        pago.monto = monto
        pago.metodo_pago = metodo
        pago.estado_pago = "completado"
        pago.fecha_pago = datetime.utcnow()
        pago.monto_comision = float(monto) * (pago.porcentaje_comision / 100.0)
    else:
        comision = float(monto) * 0.10 
        pago = models.Pago(
            incidente_id=incidente_id,
            monto=monto,
            monto_comision=comision,
            porcentaje_comision=10.0,
            metodo_pago=metodo,
            estado_pago="completado",
            fecha_pago=datetime.utcnow()
        )
        db.add(pago)

    incidente.estado = "pagado"
    db.commit()
    
    # Notificaciones para el Admin del Taller
    admin = db.query(models.Usuario).filter(models.Usuario.taller_id == incidente.taller_id, models.Usuario.rol == 'admin_taller').first()
    if admin:
        ganancia_neta = float(monto) * 0.90
        titulo = "¡Pago Recibido!"
        mensaje = f"El cliente ha pagado Bs. {monto}. Tus ganancias netas son Bs. {ganancia_neta:.1f}."
        
        # 1. Guardar en BD para el historial
        nueva_notif = models.Notificacion(
            usuario_id=admin.id,
            titulo=titulo,
            mensaje=mensaje
        )
        db.add(nueva_notif)
        db.commit()

        # 2. Enviar por Socket para alerta en tiempo real
        background_tasks.add_task(
            manager.send_personal_message, 
            {
                "tipo": "notificacion", 
                "titulo": titulo, 
                "mensaje": mensaje,
                "fecha": datetime.utcnow().strftime("%H:%M")
            }, 
            admin.id
        )
        
        # 3. Notificar al Cliente sobre el pago exitoso
        notif_cliente = models.Notificacion(
            usuario_id=incidente.cliente_id,
            titulo="Pago Exitoso",
            mensaje=f"Tu pago de Bs. {monto} vía {metodo} ha sido procesado. ¡Gracias por usar SOS Automotriz!"
        )
        db.add(notif_cliente)
        db.commit()

        background_tasks.add_task(
            manager.send_personal_message,
            {
                "tipo": "notificacion",
                "titulo": "Pago Confirmado",
                "mensaje": f"Se ha registrado tu pago de Bs. {monto}.",
                "fecha": datetime.utcnow().strftime("%H:%M")
            },
            incidente.cliente_id
        )
        
    return {"status": "success", "mensaje": "Pago completado"}

@router.post("/pagos/{incidente_id}/confirmar-efectivo")
def confirmar_pago_efectivo(
    incidente_id: UUID, 
    monto_recibido: float, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.5: Confirmación de pago en efectivo."""
    if current_user.rol not in ['admin_taller', 'super_admin']:
        raise HTTPException(status_code=403)

    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    pago = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
    
    if not incidente or not pago:
        raise HTTPException(status_code=404)

    if monto_recibido < float(pago.monto):
        raise HTTPException(status_code=400, detail="Monto insuficiente")

    cambio = monto_recibido - float(pago.monto)
    pago.estado_pago = "completado"
    pago.monto_recibido = monto_recibido
    pago.cambio = cambio
    pago.monto_comision = float(pago.monto) * (pago.porcentaje_comision / 100.0)
    
    incidente.estado = "pagado"
    db.commit()

    background_tasks.add_task(manager.send_personal_message, {"tipo": "notificacion", "titulo": "Pago Confirmado", "mensaje": f"Cambio: Bs. {cambio}"}, incidente.cliente_id)

    return {"status": "success", "cambio": cambio}

@router.get("/reporte-pdf/{incidente_id}")
def generar_pdf_incidente(incidente_id: UUID, db: Session = Depends(database.get_db)):
    """CU2.2.5: Generar comprobante."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente: raise HTTPException(status_code=404)
    
    pago = incidente.pagos[0] if incidente.pagos else None
    reporte = {
        "folio": str(incidente.id)[:8].upper(),
        "fecha": incidente.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
        "cliente": incidente.cliente.nombre if incidente.cliente else "Desconocido",
        "vehiculo": f"{incidente.vehiculo.marca} {incidente.vehiculo.modelo} ({incidente.vehiculo.placa})" if incidente.vehiculo else "N/A",
        "taller": incidente.taller.nombre if incidente.taller else "N/A",
        "diagnostico_ia": incidente.resumen_ia or "Sin evaluación IA",
        "diagnostico_tecnico": incidente.diagnostico_tecnico or "Sin observaciones finales",
        "monto_total": float(incidente.monto_total),
        "metodo_pago": pago.metodo_pago if pago else "N/A",
        "monto_recibido": float(pago.monto_recibido) if pago and pago.monto_recibido else None,
        "cambio": float(pago.cambio) if pago and pago.cambio else None
    }
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(reporte)
