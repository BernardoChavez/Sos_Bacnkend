from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

# --- 1. TABLAS DE SEGURIDAD (RBAC) ---

class Permiso(Base):
    __tablename__ = "permisos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    modulo = Column(String(100))
    caso_uso = Column(String(100))
    accion = Column(String(50))
    codigo = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)

    roles = relationship("RolPermiso", back_populates="permiso")

class RolPermiso(Base):
    __tablename__ = "rol_permisos"
    rol = Column(String(20), primary_key=True) # 'cliente', 'admin_taller', etc.
    permiso_id = Column(Integer, ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True)
    
    permiso = relationship("Permiso", back_populates="roles")

# --- MÓDULO DE TALLERES Y LOGÍSTICA ---

class Taller(Base):
    __tablename__ = "talleres"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    direccion = Column(Text)
    latitud = Column(Float)
    longitud = Column(Float)
    telefono = Column(String(20))
    capacidad_teorica = Column(Integer, default=5)
    esta_activo = Column(Boolean, default=True)
    especialidad = Column(String(100), default='General')
    horarios_atencion = Column(JSONB, nullable=True) # CU8: {'Lunes': '08:00-18:00', ...}
    poligono_cobertura = Column(JSONB, nullable=True) # CU8: GeoJSON o lista de puntos
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="taller")
    tecnicos_asignados = relationship("Tecnico", back_populates="taller")
    especialidades_rel = relationship("TallerEspecialidad", back_populates="taller")
    incidentes = relationship("Incidente", back_populates="taller")

class Especialidad(Base):
    __tablename__ = "especialidades"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_especialidad = Column(String(100), unique=True)

    talleres = relationship("TallerEspecialidad", back_populates="especialidad_ref")

class TallerEspecialidad(Base):
    __tablename__ = "taller_especialidades"
    taller_id = Column(Integer, ForeignKey("talleres.id", ondelete="CASCADE"), primary_key=True)
    especialidad_id = Column(Integer, ForeignKey("especialidades.id", ondelete="CASCADE"), primary_key=True)

    taller = relationship("Taller", back_populates="especialidades_rel")
    especialidad_ref = relationship("Especialidad", back_populates="talleres")

# --- MÓDULO DE USUARIOS ---

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150))
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    telefono = Column(String(20))
    recovery_code = Column(String(6), nullable=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(DateTime, nullable=True)
    rol = Column(String(20), default='cliente') 
    taller_id = Column(Integer, ForeignKey("talleres.id", ondelete="SET NULL"), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    taller = relationship("Taller", back_populates="usuarios")
    ficha_tecnica = relationship("Tecnico", back_populates="usuario", uselist=False)
    vehiculos = relationship("Vehiculo", back_populates="propietario")
    notificaciones = relationship("Notificacion", back_populates="usuario")

class Tecnico(Base):
    __tablename__ = "tecnicos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True)
    taller_id = Column(Integer, ForeignKey("talleres.id", ondelete="CASCADE"))
    especialidad_principal = Column(String(100))
    disponible = Column(Boolean, default=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)

    usuario = relationship("Usuario", back_populates="ficha_tecnica")
    taller = relationship("Taller", back_populates="tecnicos_asignados")
    incidentes = relationship("Incidente", back_populates="tecnico")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"))
    placa = Column(String(20), unique=True, nullable=False)
    marca = Column(String(50))
    modelo = Column(String(50))
    color = Column(String(30))
    anio = Column(Integer)

    propietario = relationship("Usuario", back_populates="vehiculos")
    incidentes = relationship("Incidente", back_populates="vehiculo")

# --- MÓDULO DE EMERGENCIAS (ESTRUCTURA CICLO 2) ---

class TipoIncidente(Base):
    __tablename__ = "tipos_incidentes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), unique=True) 
    prioridad_sugerida = Column(String(20)) 
    descripcion_protocolo = Column(Text)
    incidentes = relationship("Incidente", back_populates="tipo_incidente")

class Incidente(Base):
    __tablename__ = "incidentes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"))
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"))
    tipo_incidente_id = Column(Integer, ForeignKey("tipos_incidentes.id"))
    taller_id = Column(Integer, ForeignKey("talleres.id"))
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"))
    
    latitud = Column(Float)
    longitud = Column(Float)
    transcripcion_voz_ia = Column(Text)
    resumen_ia = Column(Text)
    categoria_ia = Column(String(50)) # CU2.2.9: Clasificación inteligente
    prioridad_final = Column(String(20))

    diagnostico_tecnico = Column(Text)
    monto_total = Column(Numeric(10, 2), default=0.0) # Costo total del trabajo
    estado = Column(String(30), default='pendiente')
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    vehiculo = relationship("Vehiculo", back_populates="incidentes")
    tipo_incidente = relationship("TipoIncidente", back_populates="incidentes")
    taller = relationship("Taller", back_populates="incidentes")
    tecnico = relationship("Tecnico", back_populates="incidentes")
    cliente = relationship("Usuario") # Relación directa para el reporte
    evidencias = relationship("Evidencia", back_populates="incidente")
    pagos = relationship("Pago", back_populates="incidente")
    resenas = relationship("Resena", back_populates="incidente")
    bitacora = relationship("BitacoraEstado", back_populates="incidente")

class Evidencia(Base):
    __tablename__ = "evidencias"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id", ondelete="CASCADE"))
    url_recurso = Column(String(500))
    tipo_recurso = Column(String(20))
    meta_datos_ia = Column(JSONB)
    fecha_subida = Column(DateTime, default=datetime.utcnow)
    incidente = relationship("Incidente", back_populates="evidencias")

class Notificacion(Base):
    __tablename__ = "notificaciones"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    titulo = Column(String(150))
    mensaje = Column(Text)
    leido = Column(Boolean, default=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)
    usuario = relationship("Usuario", back_populates="notificaciones")

class Pago(Base):
    __tablename__ = "pagos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id"), unique=True)
    monto = Column(Numeric(10, 2))
    monto_recibido = Column(Numeric(10, 2), default=0.0) # Para pagos en efectivo
    cambio = Column(Numeric(10, 2), default=0.0)         # Para pagos en efectivo
    monto_comision = Column(Numeric(10, 2), default=0.0) # CU2.2.6: Comisión para la plataforma
    porcentaje_comision = Column(Float, default=10.0) # Default 10%
    metodo_pago = Column(String(50))
    estado_pago = Column(String(50), default='pendiente')
    fecha_pago = Column(DateTime)
    incidente = relationship("Incidente", back_populates="pagos")


class Resena(Base):
    __tablename__ = "resenas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id"), unique=True)
    calificacion = Column(Integer)
    comentario = Column(Text)
    incidente = relationship("Incidente", back_populates="resenas")

class Auditoria(Base):
    __tablename__ = "auditoria"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    accion = Column(String(50)) # GET, POST, PUT, DELETE
    detalle = Column(Text) # "Consultó la lista de usuarios"
    ip = Column(String(50))
    fecha = Column(DateTime, default=datetime.utcnow)
    hora_inicio = Column(DateTime, default=datetime.utcnow)
    hora_cierre = Column(DateTime, nullable=True)
    
    usuario = relationship("Usuario")

class BitacoraEstado(Base):
    __tablename__ = "bitacora_estados"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id"))
    estado_anterior = Column(String(50))
    estado_nuevo = Column(String(50))
    usuario_cambio_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_hora = Column(DateTime, default=datetime.utcnow)
    incidente = relationship("Incidente", back_populates="bitacora")
    usuario = relationship("Usuario", foreign_keys=[usuario_cambio_id])