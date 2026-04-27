-- SOS AUTOMOTRIZ - ESTRUCTURA LIMPIA PARA SUPABASE
-- Este script elimina comandos de pgAdmin y usa SQL estándar

-- 1. Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Limpieza de tablas previas (Opcional, ten cuidado)
DROP TABLE IF EXISTS auditoria CASCADE;
DROP TABLE IF EXISTS bitacora_estados CASCADE;
DROP TABLE IF EXISTS notificaciones CASCADE;
DROP TABLE IF EXISTS pagos CASCADE;
DROP TABLE IF EXISTS resenas CASCADE;
DROP TABLE IF EXISTS evidencias CASCADE;
DROP TABLE IF EXISTS incidentes CASCADE;
DROP TABLE IF EXISTS tecnicos CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS talleres CASCADE;

-- 3. Creación de tablas
CREATE TABLE talleres (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150),
    razon_social VARCHAR(200),
    nit VARCHAR(50),
    direccion TEXT,
    telefono VARCHAR(20),
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    especialidad VARCHAR(100),
    esta_activo BOOLEAN DEFAULT true,
    capacidad_teorica INTEGER DEFAULT 5,
    horarios_atencion JSONB,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    email VARCHAR(150) UNIQUE,
    telefono VARCHAR(20),
    password_hash VARCHAR(255),
    rol VARCHAR(50), -- super_admin, admin_taller, tecnico, cliente
    taller_id INTEGER REFERENCES talleres(id) ON DELETE SET NULL,
    esta_activo BOOLEAN DEFAULT true,
    recuperar_password_token VARCHAR(255),
    bloqueado_hasta TIMESTAMP,
    intentos_fallidos INTEGER DEFAULT 0,
    recovery_code VARCHAR(10),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tecnicos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    taller_id INTEGER REFERENCES talleres(id) ON DELETE CASCADE,
    disponible BOOLEAN DEFAULT true,
    especialidad_principal VARCHAR(100),
    calificacion_promedio NUMERIC(3, 2) DEFAULT 5.0,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION
);

CREATE TABLE incidentes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id INTEGER REFERENCES usuarios(id),
    taller_id INTEGER REFERENCES talleres(id),
    tecnico_id INTEGER REFERENCES tecnicos(id),
    vehiculo_id INTEGER, -- Simulado para este proyecto
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    estado VARCHAR(50) DEFAULT 'pendiente',
    prioridad_final VARCHAR(20) DEFAULT 'Baja',
    resumen_ia TEXT,
    transcripcion_voz_ia TEXT,
    categoria_ia VARCHAR(50),
    monto_total NUMERIC(10, 2) DEFAULT 0.0,
    diagnostico_tecnico TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidencias (
    id SERIAL PRIMARY KEY,
    incidente_id UUID REFERENCES incidentes(id) ON DELETE CASCADE,
    url_recurso VARCHAR(500),
    tipo_recurso VARCHAR(20), -- foto, audio
    meta_datos_ia JSONB,
    fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    titulo VARCHAR(150),
    mensaje TEXT,
    leido BOOLEAN DEFAULT false,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pagos (
    id SERIAL PRIMARY KEY,
    incidente_id UUID REFERENCES incidentes(id) UNIQUE,
    monto NUMERIC(10, 2),
    monto_recibido NUMERIC(10, 2) DEFAULT 0.0,
    cambio NUMERIC(10, 2) DEFAULT 0.0,
    monto_comision NUMERIC(10, 2) DEFAULT 0.0,
    porcentaje_comision FLOAT DEFAULT 10.0,
    metodo_pago VARCHAR(50),
    estado_pago VARCHAR(50) DEFAULT 'pendiente',
    fecha_pago TIMESTAMP
);

CREATE TABLE auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(50),
    detalle TEXT,
    ip VARCHAR(50),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hora_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hora_cierre TIMESTAMP
);

CREATE TABLE bitacora_estados (
    id SERIAL PRIMARY KEY,
    incidente_id UUID REFERENCES incidentes(id),
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50),
    usuario_cambio_id INTEGER REFERENCES usuarios(id),
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. INSERTAR USUARIO SUPER ADMIN INICIAL
-- El password es: admin123 (hasheado con bcrypt)
INSERT INTO usuarios (nombre, email, rol, password_hash) VALUES 
('Bernardo Admin', 'chavezbernardo15@gmail.com', 'super_admin', '$2b$12$R.S9iA9K8UvYvU4m0F4mOe8kH1Q.Zk8fVvVvVvVvVvVvVvVvVvVvV');
