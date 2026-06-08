from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base
from app.models.global_models import Usuario, Vehiculo # Relaciones con el esquema public

class Taller(Base):
    __tablename__ = "talleres"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), nullable=False)
    razon_social = Column(String(200))
    nit = Column(String(50))
    direccion = Column(Text)
    latitud = Column(Float)
    longitud = Column(Float)
    telefono = Column(String(20))
    capacidad_teorica = Column(Integer, default=5)
    esta_activo = Column(Boolean, default=True)
    especialidad = Column(String(100), default='General')
    horarios_atencion = Column(JSONB, nullable=True) 
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    tecnicos_asignados = relationship("Tecnico", back_populates="taller")
    incidentes = relationship("Incidente", back_populates="taller")

class Tecnico(Base):
    __tablename__ = "tecnicos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("public.usuarios.id", ondelete="CASCADE"), unique=True)
    taller_id = Column(Integer, ForeignKey("talleres.id", ondelete="CASCADE"))
    especialidad_principal = Column(String(100))
    disponible = Column(Boolean, default=True)
    calificacion_promedio = Column(Numeric(3, 2), default=5.0)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    taller = relationship("Taller", back_populates="tecnicos_asignados")
    usuario = relationship("Usuario")
    incidentes = relationship("Incidente", back_populates="tecnico")

class Incidente(Base):
    __tablename__ = "incidentes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(Integer, ForeignKey("public.usuarios.id"))
    vehiculo_id = Column(Integer, ForeignKey("public.vehiculos.id"))
    taller_id = Column(Integer, ForeignKey("talleres.id"))
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"))
    latitud = Column(Float)
    longitud = Column(Float)
    transcripcion_voz_ia = Column(Text)
    resumen_ia = Column(Text)
    categoria_ia = Column(String(50))
    prioridad_final = Column(String(20), default='Baja')
    diagnostico_tecnico = Column(Text)
    monto_total = Column(Numeric(10, 2), default=0.0)
    estado = Column(String(30), default='pendiente')
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    taller = relationship("Taller", back_populates="incidentes")
    tecnico = relationship("Tecnico", back_populates="incidentes")
    cliente = relationship("Usuario") 
    vehiculo = relationship("Vehiculo")
    evidencias = relationship("Evidencia", back_populates="incidente")
    pagos = relationship("Pago", back_populates="incidente", uselist=False)
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

class Pago(Base):
    __tablename__ = "pagos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id"), unique=True)
    monto = Column(Numeric(10, 2))
    monto_recibido = Column(Numeric(10, 2), default=0.0) 
    cambio = Column(Numeric(10, 2), default=0.0)         
    monto_comision = Column(Numeric(10, 2), default=0.0) 
    porcentaje_comision = Column(Float, default=10.0) 
    metodo_pago = Column(String(50))
    estado_pago = Column(String(50), default='pendiente')
    fecha_pago = Column(DateTime)
    incidente = relationship("Incidente", back_populates="pagos")

class BitacoraEstado(Base):
    __tablename__ = "bitacora_estados"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id", ondelete="CASCADE"))
    estado_anterior = Column(String(50))
    estado_nuevo = Column(String(50))
    usuario_cambio_id = Column(Integer, ForeignKey("public.usuarios.id"))
    latitud_registro = Column(Float)
    longitud_registro = Column(Float)
    fecha_hora = Column(DateTime, default=datetime.utcnow)

    
    incidente = relationship("Incidente", back_populates="bitacora")
    usuario = relationship("Usuario")

class Resena(Base):
    __tablename__ = "resenas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(UUID(as_uuid=True), ForeignKey("incidentes.id", ondelete="CASCADE"), unique=True)
    calificacion = Column(Integer, nullable=False)
    comentario = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    incidente = relationship("Incidente")
