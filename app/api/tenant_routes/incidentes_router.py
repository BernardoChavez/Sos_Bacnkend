from app.core import tenant_middleware
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, aliased
from typing import List, Optional
import uuid
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from app.core import database, auth
from app.models import tenant_models as models
from app.models import global_models
from app.schemas import tenant_schemas as schemas
from app.core.socket_manager import manager

router = APIRouter(
    prefix="/incidentes",
    tags=["GestiÃ³n y AtenciÃ³n"]
)

@router.get("/cliente/mis-solicitudes")
def listar_mis_solicitudes(
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.3 & 2.2.14: Listar solicitudes y trazabilidad."""
    UsuarioTecnico = aliased(models.Usuario)
    query = db.query(
        models.Incidente, 
        models.Usuario.nombre.label("cliente_nombre"),
        UsuarioTecnico.nombre.label("tecnico_nombre")
    ).join(models.Usuario, models.Incidente.cliente_id == models.Usuario.id)\
     .outerjoin(models.Tecnico, models.Incidente.tecnico_id == models.Tecnico.id)\
     .outerjoin(UsuarioTecnico, models.Tecnico.usuario_id == UsuarioTecnico.id)\
     .options(joinedload(models.Incidente.evidencias), joinedload(models.Incidente.resenas))
    
    if current_user.rol == 'super_admin':
        pass
    elif current_user.rol == 'admin_taller':
        query = query.filter(models.Incidente.taller_id == current_user.taller_id)
    elif current_user.rol == 'tecnico':
        tecnico_rec = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
        if tecnico_rec:
            query = query.filter(models.Incidente.tecnico_id == tecnico_rec.id)
        else:
            return []
    else:
        query = query.filter(models.Incidente.cliente_id == current_user.id)
        
    results = query.order_by(models.Incidente.fecha_creacion.desc()).all()
    
    incidentes_final = []
    for incidente, cliente_nombre, tecnico_nombre in results:
        inc_dict = jsonable_encoder(incidente)
        inc_dict["cliente_nombre"] = cliente_nombre
        inc_dict["tecnico_nombre"] = tecnico_nombre or "Pendiente"
        incidentes_final.append(inc_dict)
        
    return incidentes_final

@router.get("/tecnico/mis-trabajos", response_model=List[schemas.IncidenteOut])
def listar_mis_trabajos_tecnico(
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.7: AtenciÃ³n de solicitudes para tÃ©cnicos."""
    query = db.query(models.Incidente)
    estados_activos = ['asignado', 'aceptado', 'en_camino', 'en_sitio', 'en_reparacion']
    
    if current_user.rol == 'super_admin':
        incidentes = query.filter(models.Incidente.estado.in_(estados_activos + ['pendiente'])).all()
    else:
        tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
        if not tecnico:
            return []
        incidentes = query.filter(
            models.Incidente.tecnico_id == tecnico.id,
            models.Incidente.estado.in_(estados_activos)
        ).all()
    
    return jsonable_encoder(incidentes)

@router.get("/tecnico/historial")
def historial_tecnico(
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Devuelve todo el historial del tÃ©cnico incluyendo incidentes completados."""
    query = db.query(models.Incidente).options(joinedload(models.Incidente.evidencias))
    
    if current_user.rol == 'super_admin':
        incidentes = query.all()
    else:
        tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
        if not tecnico:
            return []
        incidentes = query.filter(models.Incidente.tecnico_id == tecnico.id).all()
    
    return jsonable_encoder(incidentes)

@router.get("/taller/{taller_id}/solicitudes", response_model=List[schemas.IncidenteOut])
def listar_solicitudes_taller(
    taller_id: int,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_empresa", "admin_taller"]))
):
    """CU2.2.7: AtenciÃ³n de solicitudes para talleres."""
    if current_user.rol != 'super_admin' and current_user.taller_id != taller_id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    # Si es super_admin o admin_taller de esta empresa, devolvemos todas las solicitudes del esquema
    incidentes = db.query(models.Incidente).filter(models.Incidente.estado != 'completado').options(joinedload(models.Incidente.evidencias)).all()
    return incidentes

@router.get("/taller/{taller_id}/historial")
def historial_taller(
    taller_id: int, 
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_empresa", "admin_taller"]))
):
    """Devuelve todo el historial del taller incluyendo incidentes completados."""
    if current_user.rol != 'super_admin' and current_user.rol != 'admin_taller':
        raise HTTPException(status_code=403, detail="No tienes permiso")
        
    incidentes = db.query(models.Incidente).filter(models.Incidente.taller_id == taller_id).options(joinedload(models.Incidente.evidencias)).all()
    return incidentes

@router.patch("/{incidente_id}/gestionar/", response_model=schemas.IncidenteOut)
def gestionar_incidente(
    incidente_id: uuid.UUID,
    accion: str, # 'aceptar', 'rechazar'
    background_tasks: BackgroundTasks,
    tecnico_id: Optional[int] = None,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_empresa", "admin_taller"]))
):
    """CU2.2.7: Aceptar o rechazar servicios."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    if current_user.rol == 'super_admin':
        pass
    elif current_user.rol == 'admin_taller':
        if current_user.taller_id != incidente.taller_id:
            raise HTTPException(status_code=403, detail="No autorizado")
    else:
        raise HTTPException(status_code=403, detail="Rol no autorizado")

    estado_anterior = incidente.estado
    if accion == 'aceptar':
        incidente.estado = 'aceptado'
        if tecnico_id and tecnico_id > 0:
            tecnico = db.query(models.Tecnico).filter(models.Tecnico.id == tecnico_id).first()
            if not tecnico:
                tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == tecnico_id).first()
            
            if tecnico:
                incidente.tecnico_id = tecnico.id
                tecnico.disponible = False
                
                # Pago inicial
                nuevo_pago = models.Pago(
                    incidente_id=incidente.id,
                    monto=incidente.monto_total or 0,
                    metodo_pago='pendiente',
                    estado_pago='sin cancelar',
                    fecha_pago=datetime.utcnow()
                )
                db.add(nuevo_pago)
                
                nueva_notif = global_models.Notificacion(
                    usuario_id=tecnico.usuario_id,
                    titulo="Â¡Nuevo Trabajo Asignado!",
                    mensaje=f"El taller te ha despachado a un auxilio."
                )
                db.add(nueva_notif)
                db.commit()

                background_tasks.add_task(
                    manager.send_personal_message,
                    {
                        "tipo": "notificacion",
                        "titulo": "Â¡Nuevo Trabajo Asignado!",
                        "mensaje": "El taller te ha despachado a un auxilio.",
                        "fecha": datetime.utcnow().strftime("%H:%M")
                    },
                    tecnico.usuario_id
                )
    elif accion == 'rechazar':
        incidente.estado = 'rechazado'
        incidente.taller_id = None 
    else:
        raise HTTPException(status_code=400, detail="AcciÃ³n no vÃ¡lida")

    bitacora = models.BitacoraEstado(
        incidente_id=incidente.id,
        estado_anterior=estado_anterior,
        estado_nuevo=incidente.estado,
        usuario_cambio_id=current_user.id
    )
    db.add(bitacora)
    db.commit()
    db.refresh(incidente)

    if accion == 'aceptar':
        titulo = "TÃ©cnico en camino"
        mensaje = "El taller ha aceptado tu solicitud."
        notif = global_models.Notificacion(
            usuario_id=incidente.cliente_id,
            titulo=titulo,
            mensaje=mensaje
        )
        db.add(notif)
        db.commit()
        
        background_tasks.add_task(
            manager.send_personal_message,
            {
                "tipo": "notificacion",
                "titulo": titulo,
                "mensaje": mensaje,
                "fecha": datetime.utcnow().strftime("%H:%M")
            },
            incidente.cliente_id
        )

    return incidente

@router.post("/{incidente_id}/trazabilidad")
def cambiar_estado_trazabilidad(
    incidente_id: uuid.UUID,
    estado_nuevo: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Cambiar el estado del incidente (trazabilidad)."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente: raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    estado_anterior = incidente.estado
    incidente.estado = estado_nuevo
    db.commit()
    
    bitacora = models.BitacoraEstado(
        incidente_id=incidente.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_cambio_id=current_user.id
    )
    db.add(bitacora)
    db.commit()
    
    # Notificar
    if estado_nuevo == 'en_camino':
        titulo = "Técnico en camino"
        mensaje = "El técnico ha iniciado su recorrido hacia tu ubicación."
    elif estado_nuevo == 'en_sitio':
        titulo = "Técnico en sitio"
        mensaje = "El técnico ha llegado a tu ubicación."
    elif estado_nuevo == 'en_reparacion':
        titulo = "Reparación iniciada"
        mensaje = "El técnico ha comenzado la reparación."
    else:
        titulo = "Cambio de estado"
        mensaje = f"El servicio ahora está: {estado_nuevo}"
        
    if incidente.cliente_id:
        notif = global_models.Notificacion(
            usuario_id=incidente.cliente_id,
            titulo=titulo,
            mensaje=mensaje
        )
        db.add(notif)
        db.commit()
        
        background_tasks.add_task(
            manager.send_personal_message,
            {
                "tipo": "notificacion",
                "titulo": titulo,
                "mensaje": mensaje,
                "fecha": datetime.utcnow().strftime("%H:%M")
            },
            incidente.cliente_id
        )
    
    return {"message": f"Estado actualizado a: {estado_nuevo}"}

@router.patch("/{incidente_id}/finalizar")
def finalizar_servicio(
    incidente_id: uuid.UUID, 
    diagnostico: str, 
    monto: float,
    background_tasks: BackgroundTasks,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.3 & 2.2.7: Cierre del servicio."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente: raise HTTPException(status_code=404)

    incidente.estado = 'finalizado'
    incidente.diagnostico_tecnico = diagnostico
    incidente.monto_total = monto
    
    if incidente.tecnico_id:
        tecnico = db.query(models.Tecnico).filter(models.Tecnico.id == incidente.tecnico_id).first()
        if tecnico:
            tecnico.disponible = True
    
    db.commit()

    if incidente.cliente_id:
        notif = global_models.Notificacion(
            usuario_id=incidente.cliente_id,
            titulo="Servicio Finalizado",
            mensaje=f"Costo final: Bs. {monto}"
        )
        db.add(notif)
        db.commit()

        background_tasks.add_task(
            manager.send_personal_message,
            {
                "tipo": "notificacion",
                "titulo": "Servicio Finalizado",
                "mensaje": f"Costo final: Bs. {monto}",
                "fecha": datetime.utcnow().strftime("%H:%M")
            },
            incidente.cliente_id
        )

    return {"message": "Servicio finalizado. Esperando pago."}

@router.post("/{incidente_id}/calificar")
def calificar_servicio(
    incidente_id: uuid.UUID,
    calificacion: int, 
    comentario: str,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.14: Calificar y cerrar trazabilidad."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente: raise HTTPException(status_code=404)
    
    if incidente.cliente_id != current_user.id:
        raise HTTPException(status_code=403)

    nueva_resena = models.Resena(
        incidente_id=incidente_id,
        calificacion=calificacion,
        comentario=comentario
    )
    db.add(nueva_resena)
    db.commit()
    return {"message": "Â¡Gracias!"}
@router.get("/tecnico/historial")
def historial_tecnico(
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Devuelve todo el historial del técnico incluyendo incidentes completados."""
    query = db.query(models.Incidente).options(joinedload(models.Incidente.evidencias))
    
    if current_user.rol == 'super_admin':
        incidentes = query.all()
    else:
        tecnico = db.query(models.Tecnico).filter(models.Tecnico.usuario_id == current_user.id).first()
        if not tecnico:
            return []
        incidentes = query.filter(models.Incidente.tecnico_id == tecnico.id).all()
    
    return jsonable_encoder(incidentes)

@router.get("/taller/{taller_id}/historial")
def historial_taller(
    taller_id: int, 
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_empresa", "admin_taller"]))
):
    """Devuelve todo el historial del taller incluyendo incidentes completados."""
    if current_user.rol != 'super_admin' and current_user.rol != 'admin_taller':
        raise HTTPException(status_code=403, detail="No tienes permiso")
        
    incidentes = db.query(models.Incidente).filter(models.Incidente.taller_id == taller_id).options(joinedload(models.Incidente.evidencias)).all()
    return incidentes

@router.post("/{incidente_id}/pagos")
def procesar_pago(
    incidente_id: uuid.UUID,
    metodo: str,
    monto: float,
    background_tasks: BackgroundTasks,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.9: Procesar pago (Efectivo, Tarjeta, QR)."""
    from sqlalchemy import text
    from app.core.database import engine
    
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidente = None
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
        if incidente:
            break
            
    if not incidente:
        db.execute(text("SET search_path TO public"))
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
        
    pago = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
    
    estado_pago_nuevo = 'pendiente' if metodo.upper() == 'EFECTIVO' else 'cancelado'
    estado_incidente_nuevo = 'esperando_confirmacion_pago' if metodo.upper() == 'EFECTIVO' else 'completado'

    if not pago:
        pago = models.Pago(
            incidente_id=incidente_id,
            monto=monto,
            metodo_pago=metodo,
            estado_pago=estado_pago_nuevo,
            fecha_pago=datetime.utcnow()
        )
        db.add(pago)
    else:
        pago.metodo_pago = metodo
        pago.estado_pago = estado_pago_nuevo
        pago.monto = monto
        pago.fecha_pago = datetime.utcnow()
        
    taller_id = incidente.taller_id
    cliente_id = incidente.cliente_id
    incidente.estado = estado_incidente_nuevo
    db.commit()

    if taller_id:
        admins = db.query(global_models.Usuario).filter(
            global_models.Usuario.taller_id == taller_id,
            global_models.Usuario.rol.in_(['admin_taller', 'admin', 'superadmin'])
        ).all()
        for admin in admins:
            notif = global_models.Notificacion(
                usuario_id=admin.id,
                titulo="Pago Recibido",
                mensaje=f"El cliente ha pagado {monto} Bs mediante {metodo}."
            )
            db.add(notif)
            background_tasks.add_task(
                manager.send_personal_message,
                {
                    "tipo": "notificacion",
                    "titulo": "Pago Recibido",
                    "mensaje": f"El cliente ha pagado {monto} Bs mediante {metodo}.",
                    "fecha": datetime.utcnow().strftime("%H:%M")
                },
                admin.id
            )
            
    db.commit()
    db.execute(text("SET search_path TO public"))
    return {"message": "Pago procesado exitosamente"}

@router.post("/{incidente_id}/pagos/confirmar-efectivo")
def confirmar_pago_efectivo(
    incidente_id: uuid.UUID,
    monto_recibido: float,
    background_tasks: BackgroundTasks,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Confirmar pago en efectivo y calcular cambio."""
    pago = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="No hay pago pendiente")
        
    if float(pago.monto) > monto_recibido:
        raise HTTPException(status_code=400, detail="El monto recibido es menor al costo del servicio")
        
    cambio = monto_recibido - float(pago.monto)
    pago.estado_pago = 'cancelado'
    pago.fecha_pago = datetime.utcnow()
    
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    cliente_id = None
    if incidente:
        cliente_id = incidente.cliente_id
        incidente.estado = 'completado'
        
    db.commit()
    
    if cliente_id:
        notif = global_models.Notificacion(
            usuario_id=cliente_id,
            titulo="Pago Confirmado",
            mensaje=f"Su pago en efectivo fue confirmado. Su cambio es: {cambio} Bs."
        )
        db.add(notif)
        db.commit()
        
        background_tasks.add_task(
            manager.send_personal_message,
            {
                "tipo": "notificacion",
                "titulo": "Pago Confirmado",
                "mensaje": f"Su pago en efectivo fue confirmado. Su cambio es: {cambio} Bs.",
                "fecha": datetime.utcnow().strftime("%H:%M")
            },
            cliente_id
        )
        
    return {"message": "Pago confirmado", "cambio": cambio}

@router.post("/{incidente_id}/calificar")
def calificar_servicio(
    incidente_id: uuid.UUID,
    calificacion: int, 
    comentario: str,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """CU2.2.14: Calificar y cerrar trazabilidad."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente: raise HTTPException(status_code=404)
    
    if incidente.cliente_id != current_user.id:
        raise HTTPException(status_code=403)

    nueva_resena = models.Resena(
        incidente_id=incidente_id,
        calificacion=calificacion,
        comentario=comentario
    )
    db.add(nueva_resena)
    db.commit()
    return {"message": "Calificación registrada con éxito"}

@router.get("/{incidente_id}/reporte")
def obtener_reporte_pdf(
    incidente_id: uuid.UUID,
    db: Session = Depends(tenant_middleware.get_db_for_tenant)
):
    """Obtener datos para generar el comprobante (recibo) del servicio."""
    from sqlalchemy import text
    
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidente = None
    esquema_encontrado = None
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
        if incidente:
            esquema_encontrado = empresa.schema_name
            break
            
    if not incidente:
        db.execute(text("SET search_path TO public"))
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    # Obtener el pago
    pago = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
    
    # Obtener info global (taller y cliente)
    db.execute(text("SET search_path TO public"))
    cliente_row = db.execute(text(f"SELECT nombre FROM usuarios WHERE id = '{incidente.cliente_id}'")).first()
    cliente_nombre = cliente_row[0] if cliente_row else "Desconocido"
    
    taller_row = db.execute(text(f"SELECT nombre FROM talleres WHERE id = '{incidente.taller_id}'")).first()
    taller_nombre = taller_row[0] if taller_row else "Desconocido"
    
    vehiculo_row = db.execute(text(f"SELECT marca, modelo, placa FROM vehiculos WHERE id = '{incidente.vehiculo_id}'")).first()
    vehiculo_str = f"{vehiculo_row[0]} {vehiculo_row[1]} ({vehiculo_row[2]})" if vehiculo_row else "Desconocido"

    # Preparar el reporte
    folio = str(incidente.id).split('-')[0].upper()
    
    reporte = {
        "folio": folio,
        "fecha": incidente.fecha_creacion.strftime("%d/%m/%Y %H:%M") if incidente.fecha_creacion else "Desconocida",
        "taller": taller_nombre,
        "cliente": cliente_nombre,
        "vehiculo": vehiculo_str,
        "diagnostico_ia": incidente.resumen_ia,
        "diagnostico_tecnico": incidente.diagnostico_tecnico,
        "monto_total": incidente.monto_total or 0,
        "metodo_pago": pago.metodo_pago if pago else "NO REGISTRADO",
        "monto_recibido": pago.monto if (pago and pago.metodo_pago == 'EFECTIVO') else None,
        "cambio": (pago.monto - incidente.monto_total) if (pago and pago.metodo_pago == 'EFECTIVO' and pago.monto and incidente.monto_total) else None
    }
    
    return reporte
