from app.core import tenant_middleware
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, aliased
from typing import List, Optional
import uuid
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from app.core import database, auth
from app.models import tenant_models as models
from app.schemas import tenant_schemas as schemas
from app.core.socket_manager import manager

router = APIRouter(
    prefix="/incidentes",
    tags=["Gestión y Atención"]
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
    """CU2.2.7: Atención de solicitudes para técnicos."""
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

@router.get("/taller/{taller_id}/solicitudes", response_model=List[schemas.IncidenteOut])
def listar_solicitudes_taller(
    taller_id: int,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.check_permissions("taller.despacho.ver"))
):
    """CU2.2.7: Atención de solicitudes para talleres."""
    if current_user.rol != 'super_admin' and current_user.taller_id != taller_id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    if taller_id == 0 and current_user.rol == 'super_admin':
        incidentes = db.query(models.Incidente).filter(models.Incidente.estado != 'completado').all()
    else:
        incidentes = db.query(models.Incidente).filter(models.Incidente.taller_id == taller_id).all()
    return incidentes

@router.patch("/{incidente_id}/gestionar/", response_model=schemas.IncidenteOut)
def gestionar_incidente(
    incidente_id: uuid.UUID,
    accion: str, # 'aceptar', 'rechazar'
    background_tasks: BackgroundTasks,
    tecnico_id: Optional[int] = None,
    db: Session = Depends(tenant_middleware.get_db_for_tenant),
    current_user: models.Usuario = Depends(auth.check_permissions("taller.servicio.aceptar")) # Usamos aceptar como base, el servidor validará la lógica interna
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
                
                nueva_notif = models.Notificacion(
                    usuario_id=tecnico.usuario_id,
                    titulo="¡Nuevo Trabajo Asignado!",
                    mensaje=f"El taller te ha despachado a un auxilio."
                )
                db.add(nueva_notif)
                db.commit()

                background_tasks.add_task(
                    manager.send_personal_message,
                    {
                        "tipo": "notificacion",
                        "titulo": "¡Nuevo Trabajo Asignado!",
                        "mensaje": "El taller te ha despachado a un auxilio.",
                        "fecha": datetime.utcnow().strftime("%H:%M")
                    },
                    tecnico.usuario_id
                )
    elif accion == 'rechazar':
        incidente.estado = 'rechazado'
        incidente.taller_id = None 
    else:
        raise HTTPException(status_code=400, detail="Acción no válida")

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
        background_tasks.add_task(
            manager.send_personal_message,
            {
                "tipo": "notificacion",
                "titulo": "Técnico en camino",
                "mensaje": "El taller ha aceptado tu solicitud.",
                "fecha": datetime.utcnow().strftime("%H:%M")
            },
            incidente.cliente_id
        )

    return incidente

@router.patch("/{incidente_id}/reparar")
def empezar_reparacion(incidente_id: uuid.UUID, db: Session = Depends(tenant_middleware.get_db_for_tenant)):
    """CU2.2.7: Actualizar estado durante la atención."""
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente: raise HTTPException(status_code=404)
    incidente.estado = 'en_reparacion'
    db.commit()
    return {"message": "Estado actualizado a: Reparando"}

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
    return {"message": "¡Gracias!"}
