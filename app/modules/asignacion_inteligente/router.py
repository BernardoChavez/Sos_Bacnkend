from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import math
from datetime import datetime
from app.core import database, auth
from app.models import models
from app.modules.procesamiento_ia import engine as ia_engine
from app.core.socket_manager import manager

router = APIRouter(
    prefix="/incidentes",
    tags=["Asignación y Seguimiento"]
)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def procesar_incidente_ia(incidente_id: uuid.UUID):
    """
    CU2.2.8, 2.2.9, 2.2.10, 2.2.11, 2.2.12: Procesamiento IA y Asignación.
    """
    import asyncio
    from app.core.database import SessionLocal
    
    await asyncio.sleep(6) 
    
    db = SessionLocal()
    try:
        incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
        if not incidente:
            return

        evidencias_audio = [e for e in incidente.evidencias if e.tipo_recurso == 'audio']
        evidencias_foto = [e for e in incidente.evidencias if e.tipo_recurso == 'foto']

        transcripcion = ""
        if evidencias_audio:
            transcripcion = await ia_engine.process_voice_report(evidencias_audio[0].url_recurso)
            incidente.transcripcion_voz_ia = transcripcion

        res_ia = {
            "especialidad": "Mecánica General", 
            "prioridad": "Baja", 
            "resumen": "Analizando evidencias...",
            "diagnostico_ia": "Ficha técnica en proceso..."
        }

        if evidencias_foto:
            res_ia = await ia_engine.classify_incident_vision([e.url_recurso for e in evidencias_foto], transcripcion)
        
        categoria = res_ia.get("especialidad", "Mecánica General")
        incidente.prioridad_final = res_ia.get("prioridad", "Media")
        incidente.categoria_ia = res_ia.get("categoria", "Otros")
        incidente.resumen_ia = res_ia.get("diagnostico_ia", res_ia.get("resumen"))
        incidente.transcripcion_voz_ia = transcripcion or res_ia.get("resumen")

        # Asignación Inteligente (CU2.2.12)
        talleres = db.query(models.Taller).filter(models.Taller.esta_activo == True).all()
        
        from datetime import timedelta
        ahora_bolivia = datetime.utcnow() - timedelta(hours=4)
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dia_actual = dias_semana[ahora_bolivia.weekday()]
        
        mejor_taller_especialista = None
        mejor_taller_general = None
        distancia_min_esp = float('inf')
        distancia_min_gen = float('inf')

        for taller in talleres:
            if taller.latitud is None or taller.longitud is None:
                continue

            taller_abierto = True
            horario = taller.horarios_atencion.get(dia_actual, "") if taller.horarios_atencion else ""
            if "-" in horario:
                try:
                    apertura, cierre = horario.split("-")
                    ap_time = datetime.strptime(apertura.strip().replace('.', ':'), "%H:%M").time()
                    ci_time = datetime.strptime(cierre.strip().replace('.', ':'), "%H:%M").time()
                    ahora_time = ahora_bolivia.time()
                    if not (ap_time <= ahora_time <= ci_time):
                        taller_abierto = False
                except:
                    pass
                    
            if not taller_abierto:
                continue

            match_especialidad = (taller.especialidad.lower() in categoria.lower() or categoria.lower() in taller.especialidad.lower())
            es_general = (taller.especialidad == 'General' or taller.especialidad == 'Mecánica General')

            if match_especialidad or es_general:
                incidentes_activos = db.query(models.Incidente).filter(
                    models.Incidente.taller_id == taller.id,
                    models.Incidente.estado.in_(['asignado', 'aceptado', 'en_camino', 'en_sitio', 'en_reparacion'])
                ).count()

                if incidentes_activos < (taller.capacidad_teorica or 5):
                    tiene_tecnico_libre = db.query(models.Tecnico).filter_by(taller_id=taller.id, disponible=True).first()
                    
                    if tiene_tecnico_libre:
                        dist = haversine(incidente.latitud, incidente.longitud, taller.latitud, taller.longitud)
                        
                        if match_especialidad and dist < distancia_min_esp:
                            distancia_min_esp = dist
                            mejor_taller_especialista = taller
                        elif es_general and dist < distancia_min_gen:
                            distancia_min_gen = dist
                            mejor_taller_general = taller

        mejor_taller = mejor_taller_especialista if mejor_taller_especialista else mejor_taller_general

        if mejor_taller:
            incidente.taller_id = mejor_taller.id
            incidente.estado = 'asignado'
            
            nueva_bitacora = models.BitacoraEstado(
                incidente_id=incidente.id,
                estado_anterior='pendiente',
                estado_nuevo='asignado',
                usuario_cambio_id=incidente.cliente_id
            )
            db.add(nueva_bitacora)
            
            # 1. Notificar al Admin del Taller
            admin = db.query(models.Usuario).filter(models.Usuario.taller_id == mejor_taller.id, models.Usuario.rol == 'admin_taller').first()
            if admin:
                notif_admin = models.Notificacion(
                    usuario_id=admin.id,
                    titulo="¡Nueva Emergencia!",
                    mensaje=f"Se te ha asignado un caso de {categoria}."
                )
                db.add(notif_admin)
                await manager.send_personal_message({
                    "tipo": "notificacion",
                    "titulo": "¡Nueva Emergencia!",
                    "mensaje": f"Se te ha asignado un caso de {categoria}.",
                    "fecha": datetime.utcnow().strftime("%H:%M")
                }, admin.id)

            # 2. Notificar al Cliente
            notif_cliente = models.Notificacion(
                usuario_id=incidente.cliente_id,
                titulo="Taller Asignado",
                mensaje=f"El taller '{mejor_taller.nombre}' ha aceptado tu solicitud y está procesando el despacho."
            )
            db.add(notif_cliente)
            await manager.send_personal_message({
                "tipo": "notificacion",
                "titulo": "Taller Asignado",
                "mensaje": f"El taller '{mejor_taller.nombre}' ya está atendiendo tu caso.",
                "fecha": datetime.utcnow().strftime("%H:%M")
            }, incidente.cliente_id)

            db.commit()
        db.commit()
    except Exception as e:
        print(f"Error en procesar_incidente_ia: {e}")
    finally:
        db.close()

@router.get("/{incidente_id}/rastreo/")
def rastrear_tecnico(
    incidente_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """
    CU2.2.3 & 2.2.12: Seguimiento en mapa y asignación inteligente.
    """
    incidente = db.query(models.Incidente).filter(models.Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    tecnico = None
    distancia = 0
    eta_minutos = 0
    
    if incidente.tecnico_id:
        tecnico = db.query(models.Tecnico).filter(models.Tecnico.id == incidente.tecnico_id).first()
        if tecnico:
            distancia = haversine(tecnico.latitud or 0, tecnico.longitud or 0, incidente.latitud, incidente.longitud)
            eta_minutos = round(distancia * 2) + 5

    # Fallback para el monto: Si no está en el incidente, buscarlo en la tabla de pagos
    monto_final = float(incidente.monto_total or 0)
    if monto_final == 0:
        pago = db.query(models.Pago).filter(models.Pago.incidente_id == incidente_id).first()
        if pago: monto_final = float(pago.monto or 0)

    return {
        "incidente_id": incidente_id,
        "tecnico_id": tecnico.id if tecnico else None,
        "latitud_tecnico": tecnico.latitud if tecnico else None,
        "longitud_tecnico": tecnico.longitud if tecnico else None,
        "latitud_cliente": incidente.latitud,
        "longitud_cliente": incidente.longitud,
        "distancia_km": round(distancia, 2),
        "eta_estimado": f"{eta_minutos} min" if tecnico else "Buscando técnico...",
        "estado": incidente.estado,
        "resumen_ia": incidente.resumen_ia,
        "transcripcion_voz_ia": incidente.transcripcion_voz_ia,
        "monto_total": monto_final
    }
