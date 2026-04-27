from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
import uuid
import os
from app.core import database, auth
from app.models import models
from app.schemas import schemas
# Importamos la tarea de procesamiento IA que estará en el módulo de asignación
# Para evitar circular imports, lo ideal es que la tarea esté en un archivo 'tasks.py' o similar
# Por ahora asumimos que la movemos a asignacion_inteligente.router
# from app.modules.asignacion_inteligente.router import procesar_incidente_ia

router = APIRouter(
    prefix="/incidentes",
    tags=["Registro de Emergencias"]
)

@router.post("/solicitar/", response_model=schemas.IncidenteOut)
async def solicitar_emergencia(
    vehiculo_id: int,
    latitud: float,
    longitud: float,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions("emergencias.solicitar"))
):
    """
    CU12: Registrar nueva solicitud de emergencia vehicular.
    CU13: Capturar y enviar geolocalización.
    """
    # Verificar vehículo
    vehiculo = db.query(models.Vehiculo).filter(models.Vehiculo.id == vehiculo_id, models.Vehiculo.cliente_id == current_user.id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado o no pertenece al usuario")

    nuevo_incidente = models.Incidente(
        id=uuid.uuid4(),
        cliente_id=current_user.id,
        vehiculo_id=vehiculo_id,
        latitud=latitud,
        longitud=longitud,
        estado='pendiente'
    )
    
    db.add(nuevo_incidente)
    db.flush() 

    # Registrar estado inicial
    bitacora = models.BitacoraEstado(
        incidente_id=nuevo_incidente.id,
        estado_nuevo='pendiente',
        usuario_cambio_id=current_user.id
    )
    db.add(bitacora)
    
    db.commit()
    db.refresh(nuevo_incidente)

    # Iniciar procesamiento IA (importado dinámicamente para evitar circulares)
    from app.modules.asignacion_inteligente.router import procesar_incidente_ia
    background_tasks.add_task(procesar_incidente_ia, nuevo_incidente.id)

    return nuevo_incidente

@router.post("/{incidente_id}/evidencias/", response_model=schemas.EvidenciaOut)
async def subir_evidencia(
    incidente_id: uuid.UUID,
    tipo: str, # 'foto' o 'audio'
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions("emergencias.evidencia.subir"))
):
    """
    CU14 & CU15: Adjuntar evidencias multimedia y descripción de voz.
    """
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{incidente_id}_{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join("uploads", unique_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Generar URL real accesible
    file_url = f"http://localhost:8000/static/{unique_filename}"
    
    nueva_evidencia = models.Evidencia(
        incidente_id=incidente_id,
        url_recurso=file_url,
        tipo_recurso=tipo
    )
    db.add(nueva_evidencia)
    db.commit()
    db.refresh(nueva_evidencia)
    return nueva_evidencia
