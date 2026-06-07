from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Suscripciones ---
class SuscripcionBase(BaseModel):
    nombre: str
    max_talleres: int
    precio: float

class SuscripcionOut(SuscripcionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Empresas (Tenants) ---
class EmpresaBase(BaseModel):
    nombre: str
    slug: str

class EmpresaCreate(EmpresaBase):
    suscripcion_id: int
    admin_nombre: str
    admin_email: EmailStr
    admin_password: str

class EmpresaOut(EmpresaBase):
    id: int
    suscripcion_id: Optional[int] = None
    esta_activa: bool = True
    fecha_registro: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class EmpresaWithSuscripcionOut(EmpresaOut):
    suscripcion: Optional[SuscripcionOut] = None

# --- Especialidades ---
class EspecialidadBase(BaseModel):
    nombre_especialidad: str

class EspecialidadCreate(EspecialidadBase):
    pass

class EspecialidadOut(EspecialidadBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Usuarios ---
class UserBase(BaseModel):
    empresa_id: Optional[int] = None
    taller_id: Optional[int] = None
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    rol: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    password: Optional[str] = None
    taller_id: Optional[int] = None

class UserOut(UserBase):
    id: int
    fecha_registro: Optional[datetime] = None 
    permisos: List[str] = [] 
    model_config = ConfigDict(from_attributes=True)

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
    cliente_nombre: Optional[str] = None 
    model_config = ConfigDict(from_attributes=True)

# --- Autenticación y Matriz ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut 

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

# --- Estadísticas Globales ---
class StatsResumen(BaseModel):
    total_usuarios: int
    total_talleres: int
    total_vehiculos: int
    emergencias_hoy: int
