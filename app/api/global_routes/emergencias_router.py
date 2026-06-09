from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.core import database, auth
from app.models import global_models, tenant_models
from app.schemas import global_schemas, tenant_schemas
from app.core.ia_service import analizar_emergencia_con_ia
import uuid
import math
import os
import shutil
from datetime import datetime
from app.core.socket_manager import manager

router = APIRouter(
    prefix="/emergencias",
    tags=["Registro de Emergencias (Global)"]
)

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@router.post("/solicitar/")
def solicitar_emergencia(
    latitud: float = Form(...),
    longitud: float = Form(...),
    vehiculo_id: int = Form(...),
    audio: Optional[UploadFile] = File(None),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    """
    Algoritmo de asignación Multi-Tenant con IA (Gemini):
    1. Procesa audio/foto con Gemini para obtener especialidad y gravedad.
    2. Obtiene todas las empresas activas.
    3. Itera por sus esquemas buscando talleres con la especialidad requerida.
    4. Asigna la emergencia al taller más cercano.
    """
    archivos_para_ia = []
    if audio: archivos_para_ia.append(audio)
    if foto: archivos_para_ia.append(foto)
    
    # 1. Obtener especialidades únicas disponibles en toda la red
    especialidades_disponibles = set()
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        taller_especialidades = db.query(tenant_models.Taller.especialidad).filter(tenant_models.Taller.esta_activo == True).distinct().all()
        for esp in taller_especialidades:
            if esp[0]: especialidades_disponibles.add(esp[0])
            
    db.execute(text("SET search_path TO public"))
    lista_especialidades = list(especialidades_disponibles) if especialidades_disponibles else ["General"]
    
    resultado_ia = {"especialidad": lista_especialidades[0], "gravedad": "Alta", "resumen": "Solicitud de auxilio generada sin evidencias"}
    if archivos_para_ia:
        resultado_ia = analizar_emergencia_con_ia(archivos_para_ia, lista_especialidades)
        
    categoria_ia = resultado_ia.get("especialidad", "General")
    resumen_ia = resultado_ia.get("resumen", "Sin resumen")
    gravedad_ia = resultado_ia.get("gravedad", "Alta")
    
    # Asegurar que no sea None
    if not categoria_ia: categoria_ia = "General"
    
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    if not empresas:
        raise HTTPException(status_code=500, detail="No hay empresas registradas en el sistema")

    mejor_taller = None
    distancia_minima = float('inf')
    empresa_ganadora = None

    for empresa in empresas:
        if not empresa.schema_name: continue
        
        # Cambiamos al esquema de esta empresa temporalmente
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        
        # Buscamos talleres activos que coincidan con la especialidad
        talleres = db.query(tenant_models.Taller).filter(
            tenant_models.Taller.esta_activo == True,
            tenant_models.Taller.especialidad.ilike(f"%{categoria_ia}%")
        ).all()
        
        for taller in talleres:
            if taller.latitud and taller.longitud:
                dist = calcular_distancia(latitud, longitud, taller.latitud, taller.longitud)
                if dist < distancia_minima:
                    distancia_minima = dist
                    mejor_taller = taller
                    empresa_ganadora = empresa
                    
    # FALLBACK: Si no hay talleres con esa especialidad exacta, buscamos el más cercano de CUALQUIER especialidad
    if not mejor_taller:
        distancia_minima = float('inf')
        for empresa in empresas:
            if not empresa.schema_name: continue
            db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
            talleres_activos = db.query(tenant_models.Taller).filter(tenant_models.Taller.esta_activo == True).all()
            for taller in talleres_activos:
                if taller.latitud and taller.longitud:
                    dist = calcular_distancia(latitud, longitud, taller.latitud, taller.longitud)
                    if dist < distancia_minima:
                        distancia_minima = dist
                        mejor_taller = taller
                        empresa_ganadora = empresa

    if not mejor_taller:
        # Volvemos a public antes de fallar
        db.execute(text("SET search_path TO public"))
        raise HTTPException(status_code=404, detail="No se encontraron talleres disponibles para esta especialidad cerca de ti.")

    # Nos aseguramos de estar en el esquema del ganador para registrar el incidente
    db.execute(text(f"SET search_path TO {empresa_ganadora.schema_name}, public"))
    
    nuevo_incidente = tenant_models.Incidente(
        cliente_id=current_user.id,
        vehiculo_id=vehiculo_id,
        taller_id=mejor_taller.id,
        latitud=latitud,
        longitud=longitud,
        categoria_ia=categoria_ia,
        resumen_ia=resumen_ia,
        estado="pendiente",
        prioridad_final=gravedad_ia
    )
    
    db.add(nuevo_incidente)
    db.flush()
    
    # Guardar archivos
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        
    for arch in archivos_para_ia:
        arch.file.seek(0)
        file_path = os.path.join(uploads_dir, f"{nuevo_incidente.id}_{arch.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(arch.file, buffer)
            
        tipo_rec = 'audio' if 'audio' in arch.content_type else 'foto'
        
        nueva_evidencia = tenant_models.Evidencia(
            incidente_id=nuevo_incidente.id,
            tipo_recurso=tipo_rec,
            url_recurso=f"/uploads/{nuevo_incidente.id}_{arch.filename}",
            meta_datos_ia=resultado_ia
        )
        db.add(nueva_evidencia)

    # Leemos los datos de nombre antes del commit para evitar que SQLAlchemy
    # intente recargarlos desde la BD cuando el search_path ya está en public
    taller_nombre = mejor_taller.nombre
    empresa_nombre = empresa_ganadora.nombre

    db.commit()
    
    # Después del commit, restauramos el search_path para poder hacer el refresh correctamente
    db.execute(text(f"SET search_path TO {empresa_ganadora.schema_name}, public"))
    db.refresh(nuevo_incidente)
    incidente_id_final = nuevo_incidente.id
    
    # Volver a public por seguridad al final de la request
    db.execute(text("SET search_path TO public"))

    return {
        "message": "Emergencia asignada exitosamente",
        "taller_asignado": taller_nombre,
        "empresa": empresa_nombre,
        "distancia_km": round(distancia_minima, 2),
        "incidente_id": incidente_id_final
    }

from sqlalchemy.orm import joinedload, aliased
from fastapi.encoders import jsonable_encoder
from fastapi import UploadFile, File
from pydantic import BaseModel

class RespuestaCotizacionGlobal(BaseModel):
    aceptada: bool


@router.get("/cliente/mis-solicitudes")
def listar_mis_solicitudes_global(
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidentes_final = []
    
    UsuarioTecnico = aliased(global_models.Usuario)
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        
        results = db.query(
            tenant_models.Incidente, 
            global_models.Usuario.nombre.label("cliente_nombre"),
            UsuarioTecnico.nombre.label("tecnico_nombre")
        ).join(global_models.Usuario, tenant_models.Incidente.cliente_id == global_models.Usuario.id)\
         .outerjoin(tenant_models.Tecnico, tenant_models.Incidente.tecnico_id == tenant_models.Tecnico.id)\
         .outerjoin(UsuarioTecnico, tenant_models.Tecnico.usuario_id == UsuarioTecnico.id)\
         .options(joinedload(tenant_models.Incidente.evidencias))\
         .filter(tenant_models.Incidente.cliente_id == current_user.id)\
         .all()
         
        for incidente, cliente_nombre, tecnico_nombre in results:
            inc_dict = jsonable_encoder(incidente)
            inc_dict["cliente_nombre"] = cliente_nombre
            inc_dict["tecnico_nombre"] = tecnico_nombre or "Pendiente"
            inc_dict["empresa_nombre"] = empresa.nombre
            incidentes_final.append(inc_dict)

    db.execute(text("SET search_path TO public"))
    
    # Sort by fecha_creacion descending
    incidentes_final.sort(key=lambda x: x["fecha_creacion"], reverse=True)
    return incidentes_final

@router.post("/cliente/{incidente_id}/calificar")
def calificar_servicio_global(
    incidente_id: uuid.UUID,
    calificacion: int, 
    comentario: str,
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidente = None
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        incidente = db.query(tenant_models.Incidente).filter(tenant_models.Incidente.id == incidente_id).first()
        if incidente:
            if incidente.cliente_id != current_user.id:
                db.execute(text("SET search_path TO public"))
                raise HTTPException(status_code=403, detail="No puedes calificar un incidente que no es tuyo")
                
            nueva_resena = tenant_models.Resena(
                incidente_id=incidente_id,
                calificacion=calificacion,
                comentario=comentario
            )
            db.add(nueva_resena)
            db.commit()
            break

    db.execute(text("SET search_path TO public"))
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
        
    return {"message": "¡Gracias por tu reseña!"}

@router.post("/cliente/{incidente_id}/evidencias/")
def subir_evidencia_global(
    incidente_id: uuid.UUID,
    tipo: str,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidente = None
    url_recurso = f"/uploads/{file.filename}"
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        incidente = db.query(tenant_models.Incidente).filter(tenant_models.Incidente.id == incidente_id).first()
        if incidente:
            nueva_evidencia = tenant_models.Evidencia(
                incidente_id=incidente_id,
                tipo_recurso=tipo,
                url_recurso=url_recurso
            )
            db.add(nueva_evidencia)
            db.commit()
            break

    db.execute(text("SET search_path TO public"))
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
        
    return {"message": "Evidencia subida", "url": url_recurso}

@router.get("/cliente/{incidente_id}/rastreo/")
def get_rastreo_global(
    incidente_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidente = None
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        incidente = db.query(tenant_models.Incidente).filter(tenant_models.Incidente.id == incidente_id).first()
        if incidente:
            base_resp = {
                "latitud_cliente": incidente.latitud,
                "longitud_cliente": incidente.longitud,
                "estado": incidente.estado,
                "resumen_ia": incidente.resumen_ia,
                "transcripcion_voz_ia": incidente.transcripcion_voz_ia or incidente.resumen_ia,
                "monto_total": float(incidente.monto_total) if incidente.monto_total else 0.0,
                "cotizacion_monto": float(incidente.cotizacion_monto) if incidente.cotizacion_monto else 0.0,
                "cotizacion_detalle": incidente.cotizacion_detalle,
                "distancia_km": 0.0,
                "eta_estimado": "Calculando..."
            }
            if not incidente.tecnico_id:
                db.execute(text("SET search_path TO public"))
                return base_resp
                
            tecnico = db.query(tenant_models.Tecnico).filter(tenant_models.Tecnico.id == incidente.tecnico_id).first()
            if tecnico:
                base_resp["latitud_tecnico"] = tecnico.latitud
                base_resp["longitud_tecnico"] = tecnico.longitud
                if tecnico.latitud and tecnico.longitud and incidente.latitud and incidente.longitud:
                    dist = calcular_distancia(incidente.latitud, incidente.longitud, tecnico.latitud, tecnico.longitud)
                    base_resp["distancia_km"] = round(dist, 1)
                    base_resp["eta_estimado"] = f"{int(dist * 3)} min"
                    
            db.execute(text("SET search_path TO public"))
            return base_resp

    db.execute(text("SET search_path TO public"))
    raise HTTPException(status_code=404, detail="Incidente no encontrado")

@router.post("/cliente/{incidente_id}/responder-cotizacion")
def responder_cotizacion_global(
    incidente_id: uuid.UUID,
    respuesta: RespuestaCotizacionGlobal,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    incidente = None
    
    for empresa in empresas:
        if not empresa.schema_name: continue
        db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
        incidente = db.query(tenant_models.Incidente).filter(tenant_models.Incidente.id == incidente_id).first()
        if incidente:
            break
            
    if not incidente:
        db.execute(text("SET search_path TO public"))
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
        
    estado_anterior = incidente.estado
    
    if respuesta.aceptada:
        nuevo_estado = 'en_camino'
        incidente.estado = nuevo_estado
        msg_tecnico = "El cliente ACEPTÓ la cotización. Dirígete a la ubicación."
    else:
        nuevo_estado = 'cancelado'
        incidente.estado = nuevo_estado
        msg_tecnico = "El cliente RECHAZÓ la cotización. El servicio fue cancelado."
        
        if incidente.tecnico_id:
            tecnico = db.query(tenant_models.Tecnico).filter(tenant_models.Tecnico.id == incidente.tecnico_id).first()
            if tecnico:
                tecnico.disponible = True
                
        pago = db.query(tenant_models.Pago).filter(tenant_models.Pago.incidente_id == incidente.id).first()
        if pago:
            pago.estado_pago = 'cancelado'
            
    bitacora = tenant_models.BitacoraEstado(
        incidente_id=incidente.id,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        usuario_cambio_id=current_user.id
    )
    db.add(bitacora)
    db.commit()
    
    if incidente.tecnico_id:
        tecnico = db.query(tenant_models.Tecnico).filter(tenant_models.Tecnico.id == incidente.tecnico_id).first()
        if tecnico and tecnico.usuario_id:
            notif = global_models.Notificacion(
                usuario_id=tecnico.usuario_id,
                titulo="Respuesta a Cotización",
                mensaje=msg_tecnico
            )
            db.add(notif)
            db.commit()
            
            background_tasks.add_task(
                manager.send_personal_message,
                {
                    "tipo": "COTIZACION_RESPUESTA",
                    "titulo": "Respuesta a Cotización",
                    "mensaje": msg_tecnico,
                    "aceptada": respuesta.aceptada,
                    "incidente_id": str(incidente.id),
                    "fecha": datetime.utcnow().strftime("%H:%M")
                },
                tecnico.usuario_id
            )
            
    db.execute(text("SET search_path TO public"))
    return {"message": "Respuesta procesada correctamente", "estado": nuevo_estado}
