from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Permiso(Base):
    __tablename__ = "permisos"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    modulo = Column(String(100))
    caso_uso = Column(String(100))
    accion = Column(String(50))
    codigo = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    roles = relationship("RolPermiso", back_populates="permiso")

class RolPermiso(Base):
    __tablename__ = "rol_permisos"
    __table_args__ = {"schema": "public"}
    rol = Column(String(20), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("public.permisos.id", ondelete="CASCADE"), primary_key=True)
    permiso = relationship("Permiso", back_populates="roles")

class Suscripcion(Base):
    __tablename__ = "suscripciones"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100))
    max_talleres = Column(Integer)
    precio = Column(Numeric(10, 2), default=0.0)
    empresas = relationship("Empresa", back_populates="suscripcion")

class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), unique=True)
    slug = Column(String(150), unique=True)
    schema_name = Column(String(50), unique=True)
    suscripcion_id = Column(Integer, ForeignKey("public.suscripciones.id", ondelete="SET NULL"), nullable=True)
    esta_activa = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    suscripcion = relationship("Suscripcion", back_populates="empresas")
    usuarios = relationship("Usuario", back_populates="empresa")

class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("public.empresas.id", ondelete="CASCADE"), nullable=True)
    taller_id = Column(Integer, nullable=True)
    nombre = Column(String(150))
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    telefono = Column(String(20))
    recovery_code = Column(String(6), nullable=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(DateTime, nullable=True)
    rol = Column(String(50), default='cliente') 
    esta_activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    empresa = relationship("Empresa", back_populates="usuarios")
    vehiculos = relationship("Vehiculo", back_populates="propietario")
    notificaciones = relationship("Notificacion", back_populates="usuario")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("public.usuarios.id", ondelete="CASCADE"))
    placa = Column(String(20), unique=True, nullable=False)
    marca = Column(String(50))
    modelo = Column(String(50))
    color = Column(String(30))
    anio = Column(Integer)
    propietario = relationship("Usuario", back_populates="vehiculos")

class TipoIncidente(Base):
    __tablename__ = "tipos_incidentes"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), unique=True) 
    prioridad_sugerida = Column(String(20)) 
    descripcion_protocolo = Column(Text)

class Notificacion(Base):
    __tablename__ = "notificaciones"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("public.usuarios.id"))
    titulo = Column(String(150))
    mensaje = Column(Text)
    leido = Column(Boolean, default=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)
    usuario = relationship("Usuario", back_populates="notificaciones")

class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("public.usuarios.id", ondelete="SET NULL"), nullable=True)
    accion = Column(String(50))
    detalle = Column(Text)
    ip = Column(String(50))
    fecha = Column(DateTime, default=datetime.utcnow)
    hora_inicio = Column(DateTime, default=datetime.utcnow)
    hora_cierre = Column(DateTime, nullable=True)
    usuario = relationship("Usuario")

class Especialidad(Base):
    __tablename__ = "especialidades"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_especialidad = Column(String(100), unique=True)
