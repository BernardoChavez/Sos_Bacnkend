-- SOS AUTOMOTRIZ - ARQUITECTURA MULTI-TENANT POR ESQUEMAS

-- 1. Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Limpieza Completa (CUIDADO: Borra toda la BD actual)
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- =========================================================
-- PARTE 1: TABLAS GLOBALES (SCHEMA: public)
-- =========================================================

CREATE TABLE public.suscripciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    max_talleres INTEGER,
    precio NUMERIC(10, 2) DEFAULT 0.0
);

CREATE TABLE public.empresas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE,
    slug VARCHAR(150) UNIQUE,
    schema_name VARCHAR(50) UNIQUE, -- Nombre del esquema físico (ej. tenant_1)
    suscripcion_id INTEGER REFERENCES public.suscripciones(id) ON DELETE SET NULL,
    esta_activa BOOLEAN DEFAULT true,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.usuarios (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES public.empresas(id) ON DELETE CASCADE, -- Nulo para clientes globales
    nombre VARCHAR(100),
    email VARCHAR(150) UNIQUE,
    telefono VARCHAR(20),
    password_hash VARCHAR(255),
    rol VARCHAR(50), -- super_admin_global, super_admin_empresa, admin_taller, tecnico, cliente
    esta_activo BOOLEAN DEFAULT true,
    recuperar_password_token VARCHAR(255),
    bloqueado_hasta TIMESTAMP,
    intentos_fallidos INTEGER DEFAULT 0,
    recovery_code VARCHAR(10),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- PARTE 2: FUNCION GENERADORA DE ESQUEMAS (MAGIA MULTI-TENANT)
-- =========================================================
-- Esta función crea un esquema completamente aislado para una empresa
-- y construye todas las tablas necesarias adentro.

CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_name TEXT)
RETURNS void AS $$
BEGIN
    -- 1. Crear el esquema
    EXECUTE 'CREATE SCHEMA IF NOT EXISTS ' || quote_ident(tenant_name);
    
    -- 2. Crear Talleres en el esquema del tenant
    EXECUTE 'CREATE TABLE ' || quote_ident(tenant_name) || '.talleres (
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
    )';

    -- 3. Crear Técnicos en el esquema del tenant
    EXECUTE 'CREATE TABLE ' || quote_ident(tenant_name) || '.tecnicos (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER, -- FK Logica hacia public.usuarios
        taller_id INTEGER REFERENCES ' || quote_ident(tenant_name) || '.talleres(id) ON DELETE CASCADE,
        disponible BOOLEAN DEFAULT true,
        especialidad_principal VARCHAR(100),
        calificacion_promedio NUMERIC(3, 2) DEFAULT 5.0,
        latitud DOUBLE PRECISION,
        longitud DOUBLE PRECISION
    )';

    -- 4. Crear Incidentes (Emergencias)
    EXECUTE 'CREATE TABLE ' || quote_ident(tenant_name) || '.incidentes (
        id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
        cliente_id INTEGER, -- FK Logica a public.usuarios (Cliente Global)
        taller_id INTEGER REFERENCES ' || quote_ident(tenant_name) || '.talleres(id),
        tecnico_id INTEGER REFERENCES ' || quote_ident(tenant_name) || '.tecnicos(id),
        vehiculo_id INTEGER, -- Asumiendo que vehiculos sigue siendo global o simulado
        latitud DOUBLE PRECISION,
        longitud DOUBLE PRECISION,
        estado VARCHAR(50) DEFAULT ''pendiente'',
        prioridad_final VARCHAR(20) DEFAULT ''Baja'',
        resumen_ia TEXT,
        transcripcion_voz_ia TEXT,
        categoria_ia VARCHAR(50),
        monto_total NUMERIC(10, 2) DEFAULT 0.0,
        diagnostico_tecnico TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )';
    
    -- 5. Crear Evidencias
    EXECUTE 'CREATE TABLE ' || quote_ident(tenant_name) || '.evidencias (
        id SERIAL PRIMARY KEY,
        incidente_id UUID REFERENCES ' || quote_ident(tenant_name) || '.incidentes(id) ON DELETE CASCADE,
        url_recurso VARCHAR(500),
        tipo_recurso VARCHAR(20),
        meta_datos_ia JSONB,
        fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )';
    
    -- 6. Crear Pagos
    EXECUTE 'CREATE TABLE ' || quote_ident(tenant_name) || '.pagos (
        id SERIAL PRIMARY KEY,
        incidente_id UUID REFERENCES ' || quote_ident(tenant_name) || '.incidentes(id) UNIQUE,
        monto NUMERIC(10, 2),
        monto_recibido NUMERIC(10, 2) DEFAULT 0.0,
        cambio NUMERIC(10, 2) DEFAULT 0.0,
        monto_comision NUMERIC(10, 2) DEFAULT 0.0,
        porcentaje_comision FLOAT DEFAULT 10.0,
        metodo_pago VARCHAR(50),
        estado_pago VARCHAR(50) DEFAULT ''pendiente'',
        fecha_pago TIMESTAMP
    )';

    -- 7. Crear Bitácora de Estados
    EXECUTE 'CREATE TABLE ' || quote_ident(tenant_name) || '.bitacora_estados (
        id SERIAL PRIMARY KEY,
        incidente_id UUID REFERENCES ' || quote_ident(tenant_name) || '.incidentes(id),
        estado_anterior VARCHAR(50),
        estado_nuevo VARCHAR(50),
        usuario_cambio_id INTEGER, -- FK Logica a public.usuarios
        fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )';
    
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- PARTE 3: DATOS INICIALES (SEMILLAS)
-- =========================================================

INSERT INTO public.suscripciones (nombre, max_talleres, precio) VALUES 
('Free', 1, 0.0),
('Pro', 3, 49.99),
('Premium', 9999, 99.99);

-- Usuario Super Admin (El password es: admin123)
INSERT INTO public.usuarios (nombre, email, rol, password_hash) VALUES 
('Bernardo Admin Global', 'chavezbernardo15@gmail.com', 'super_admin_global', '$2b$12$R.S9iA9K8UvYvU4m0F4mOe8kH1Q.Zk8fVvVvVvVvVvVvVvVvVvVvV');
