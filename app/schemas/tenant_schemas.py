from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid
from app.schemas.global_schemas import UserOut

# --- Talleres ---
class TallerBase(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    telefono: Optional[str] = None
    capacidad_teorica: Optional[int] = 5
    esta_activo: bool = True
    especialidad: Optional[str] = 'General'
    horarios_atencion: Optional[dict] = None

class TallerCreate(TallerBase):
    pass

class TallerUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    telefono: Optional[str] = None
    especialidad: Optional[str] = None
    capacidad_teorica: Optional[int] = None
    esta_activo: Optional[bool] = None
    horarios_atencion: Optional[dict] = None

class TallerOut(TallerBase):
    id: int
    fecha_registro: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TallerWithAdminOut(TallerOut):
    admin_nombre: Optional[str] = None

class UserWithTallerOut(UserOut):
    taller_nombre: Optional[str] = None 
    disponible: Optional[bool] = None   

# --- Técnicos ---
class TecnicoBase(BaseModel):
    usuario_id: int
    taller_id: Optional[int] = None
    especialidad_principal: Optional[str] = "General"
    disponible: bool = True

class TecnicoCreate(TecnicoBase):
    pass

class TecnicoUpdate(BaseModel):
    especialidad_principal: Optional[str] = None
    disponible: Optional[bool] = None

class TecnicoOut(TecnicoBase):
    id: int
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

# --- RESEÑAS ---
class ResenaOut(BaseModel):
    id: int
    calificacion: int
    comentario: Optional[str] = None
    fecha_resena: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- EMERGENCIAS E IA ---
class EvidenciaBase(BaseModel):
    url_recurso: str
    tipo_recurso: str 

class EvidenciaOut(EvidenciaBase):
    id: int
    fecha_subida: datetime
    model_config = ConfigDict(from_attributes=True)

class IncidenteBase(BaseModel):
    vehiculo_id: int
    latitud: float
    longitud: float

class IncidenteCreate(IncidenteBase):
    pass

class IncidenteUpdate(BaseModel):
    estado: Optional[str] = None
    taller_id: Optional[int] = None
    tecnico_id: Optional[int] = None
    prioridad_final: Optional[str] = None

class IncidenteOut(IncidenteBase):
    id: uuid.UUID
    cliente_id: int
    taller_id: Optional[int]
    tecnico_id: Optional[int]
    estado: str
    fecha_creacion: datetime
    resumen_ia: Optional[str]
    prioridad_final: Optional[str]
    transcripcion_voz_ia: Optional[str]
    diagnostico_tecnico: Optional[str]
    monto_total: Optional[float]
    evidencias: List[EvidenciaOut] = []
    model_config = ConfigDict(from_attributes=True)

class BitacoraEstadoOut(BaseModel):
    id: int
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    usuario_cambio_id: int
    fecha_hora: datetime
    model_config = ConfigDict(from_attributes=True)
