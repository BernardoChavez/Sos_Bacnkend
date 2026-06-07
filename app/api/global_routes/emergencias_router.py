from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core import database, auth
from app.models import global_models, tenant_models
from app.schemas import global_schemas, tenant_schemas
import uuid
import math
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
    latitud: float,
    longitud: float,
    vehiculo_id: int,
    categoria_ia: str = "General", # En producción lo determinaría la IA con el audio/foto
    resumen_ia: str = "Solicitud de auxilio generada",
    db: Session = Depends(database.get_db),
    current_user: global_models.Usuario = Depends(auth.get_current_user)
):
    """
    Algoritmo de asignación Multi-Tenant:
    1. Obtiene todas las empresas activas.
    2. Itera por sus esquemas buscando talleres con la especialidad requerida.
    3. Calcula la distancia.
    4. Asigna la emergencia al taller más cercano en el esquema correspondiente.
    """
    
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
        prioridad_final="Alta"
    )
    
    db.add(nuevo_incidente)
    db.commit()
    db.refresh(nuevo_incidente)
    
    # Aquí podríamos notificar por WebSockets a los admins de ese taller
    # Usando el manager
    
    # Volver a public por seguridad al final de la request
    db.execute(text("SET search_path TO public"))

    return {
        "message": "Emergencia asignada exitosamente",
        "taller_asignado": mejor_taller.nombre,
        "empresa": empresa_ganadora.nombre,
        "distancia_km": round(distancia_minima, 2),
        "incidente_id": nuevo_incidente.id
    }
