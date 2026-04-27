from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
import uuid

# --- Especialidades ---
class EspecialidadBase(BaseModel):
    nombre_especialidad: str

class EspecialidadCreate(EspecialidadBase):
    pass

class EspecialidadOut(EspecialidadBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

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
    poligono_cobertura: Optional[dict] = None

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
    poligono_cobertura: Optional[dict] = None

class TallerOut(TallerBase):
    id: int
    fecha_registro: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TallerWithAdminOut(TallerOut):
    admin_nombre: Optional[str] = None


# --- Usuarios ---
class UserBase(BaseModel):
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    rol: str
    taller_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    fecha_registro: Optional[datetime] = None 
    permisos: List[str] = [] 
    model_config = ConfigDict(from_attributes=True)

class UserWithTallerOut(UserOut):
    taller_nombre: Optional[str] = None # Solo para listados detallados
    disponible: Optional[bool] = None   # Estado de disponibilidad del técnico

# --- Vehículos ---
class VehiculoBase(BaseModel):
    placa: str
    marca: str
    modelo: str
    color: Optional[str] = None
    anio: Optional[int] = None

class VehiculoCreate(VehiculoBase):
    cliente_id: Optional[int] = None

class VehiculoUpdate(BaseModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    color: Optional[str] = None
    anio: Optional[int] = None

class VehiculoOut(VehiculoBase):
    id: int
    cliente_id: int
    cliente_nombre: Optional[str] = None # Para el Super Admin
    model_config = ConfigDict(from_attributes=True)

# --- Autenticación y Matriz ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut # Usa el schema UserOut ya corregido

class PermisoOut(BaseModel):
    id: int
    codigo: str
    descripcion: str
    model_config = ConfigDict(from_attributes=True)

class MatrizItem(BaseModel):
    id: int
    codigo: str
    descripcion: str
    cliente: bool
    admin_taller: bool
    tecnico: bool

class PasswordRecover(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

class PasswordVerifyCode(BaseModel):
    email: EmailStr
    code: str

class PasswordResetCode(BaseModel):
    email: EmailStr
    code: str
    new_password: str

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

# --- Estadísticas (Dashboard CU21) ---
class StatsResumen(BaseModel):
    total_usuarios: int
    total_talleres: int
    total_vehiculos: int
    emergencias_hoy: int

# --- RESEÑAS ---
class ResenaOut(BaseModel):
    id: int
    calificacion: int
    comentario: Optional[str] = None
    fecha_resena: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- CICLO 2: EMERGENCIAS E IA ---

class EvidenciaBase(BaseModel):
    url_recurso: str
    tipo_recurso: str # 'foto', 'audio'

class EvidenciaOut(EvidenciaBase):
    id: int
    fecha_subida: datetime
    model_config = ConfigDict(from_attributes=True)

class IncidenteBase(BaseModel):
    vehiculo_id: int
    latitud: float
    longitud: float

class IncidenteCreate(IncidenteBase):
    # El cliente_id se tomará del token
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
    resenas: List[ResenaOut] = [] # Ahora usamos el esquema real
    model_config = ConfigDict(from_attributes=True)

class BitacoraEstadoOut(BaseModel):
    id: int
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    usuario_cambio_id: int
    fecha_hora: datetime
    model_config = ConfigDict(from_attributes=True)