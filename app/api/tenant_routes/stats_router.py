from app.core import tenant_middleware
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core import database, auth
from app.models import tenant_models as models

router = APIRouter(prefix="/stats", tags=["Dashboard"])

@router.get("/resumen")
def obtener_resumen(db: Session = Depends(tenant_middleware.get_db_for_tenant), 
                    user=Depends(auth.get_current_user)):
    if user.rol == "super_admin":
        total_recaudado = db.query(func.sum(models.Pago.monto_comision)).filter(models.Pago.estado_pago == 'completado').scalar() or 0
        
        # Cálculo de reputación para el Super Admin
        top_talleres = db.query(
            models.Taller.nombre,
            func.avg(models.Resena.calificacion).label("promedio"),
            func.count(models.Resena.id).label("total_resenas")
        ).join(models.Incidente, models.Taller.id == models.Incidente.taller_id)\
         .join(models.Resena, models.Incidente.id == models.Resena.incidente_id)\
         .group_by(models.Taller.id)\
         .order_by(func.avg(models.Resena.calificacion).desc())\
         .limit(5).all()

        ranking = [{"nombre": t.nombre, "promedio": round(float(t.promedio), 1), "votos": t.total_resenas} for t in top_talleres]

        return {
            "usuarios": db.query(models.Usuario).count(),
            "talleres": db.query(models.Taller).count(),
            "vehiculos": db.query(models.Vehiculo).count(),
            "emergencias": db.query(models.Incidente).count(),
            "ingresos": float(total_recaudado),
            "ranking_talleres": ranking
        }
    elif user.rol == "admin_taller":
        taller = db.query(models.Taller).filter_by(id=user.taller_id).first()
        
        # Ingresos del taller: total pagado menos la comisión de la web
        ingresos_taller = db.query(func.sum(models.Pago.monto - models.Pago.monto_comision))\
                            .join(models.Incidente)\
                            .filter(models.Incidente.taller_id == user.taller_id, models.Pago.estado_pago == 'completado').scalar() or 0
                            
        # Evaluar estado dinámico
        estado_dinamico = "Inactivo"
        if taller and taller.esta_activo:
            estado_dinamico = "Activo"
            from datetime import timedelta, datetime
            ahora_bolivia = datetime.utcnow() - timedelta(hours=4)
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dia_actual = dias_semana[ahora_bolivia.weekday()]
            hora_actual_str = ahora_bolivia.strftime("%H:%M")
            horario = taller.horarios_atencion.get(dia_actual, "") if taller.horarios_atencion else ""
            if "-" in horario:
                try:
                    apertura, cierre = horario.split("-")
                    ap_time = datetime.strptime(apertura.strip().replace('.', ':'), "%H:%M").time()
                    ci_time = datetime.strptime(cierre.strip().replace('.', ':'), "%H:%M").time()
                    ahora_time = ahora_bolivia.time()
                    if not (ap_time <= ahora_time <= ci_time):
                        estado_dinamico = "Cerrado"
                except Exception as e:
                    pass
                    
        return {
            "tecnicos": db.query(models.Usuario).filter_by(taller_id=user.taller_id, rol="tecnico").count(),
            "servicios_hoy": db.query(models.Incidente).filter(models.Incidente.taller_id == user.taller_id).count(),
            "estado_taller": estado_dinamico,
            "ingresos": float(ingresos_taller)
        }
    elif user.rol == "cliente":
        return {
            "vehiculos": db.query(models.Vehiculo).filter_by(cliente_id=user.id).count(),
            "servicios_activos": db.query(models.Incidente).filter(models.Incidente.cliente_id == user.id, models.Incidente.estado != 'completado').count()
        }
    elif user.rol == "tecnico":
        tecnico = db.query(models.Tecnico).filter_by(usuario_id=user.id).first()
        return {
            "disponible": tecnico.disponible if tecnico else False,
            "especialidad": tecnico.especialidad_principal if tecnico else "General",
            "servicios_asignados": db.query(models.Incidente).filter_by(tecnico_id=tecnico.id if tecnico else None).count()
        }
    return {}

@router.get("/resenas")
def obtener_todas_las_resenas(db: Session = Depends(tenant_middleware.get_db_for_tenant), 
                             user=Depends(auth.get_current_user)):
    query = db.query(
        models.Resena.calificacion,
        models.Resena.comentario,
        models.Incidente.fecha_creacion.label("fecha"),
        models.Usuario.nombre.label("cliente"),
        models.Taller.nombre.label("taller"),
        models.Taller.id.label("taller_id")
    ).join(models.Incidente, models.Resena.incidente_id == models.Incidente.id)\
     .join(models.Usuario, models.Incidente.cliente_id == models.Usuario.id)\
     .join(models.Taller, models.Incidente.taller_id == models.Taller.id)

    if user.rol == "admin_taller":
        query = query.filter(models.Taller.id == user.taller_id)
    
    resenas = query.order_by(models.Incidente.fecha_creacion.desc()).all()
    
    return [
        {
            "calificacion": r.calificacion,
            "comentario": r.comentario,
            "fecha": r.fecha.strftime("%Y-%m-%d %H:%M"),
            "cliente": r.cliente,
            "taller": r.taller
        } for r in resenas
    ]
