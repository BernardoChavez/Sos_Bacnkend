from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.database import engine, Base
from app.models import models
from app.core.socket_manager import manager

# --- IMPORTACIÓN MODULAR (ARQUITECTURA DE PAQUETES) ---
from app.modules.usuarios_vehiculos import auth_router, usuarios_router, vehiculos_router, permisos_router
from app.modules.talleres_tecnicos import talleres_router, tecnicos_router, especialidades_router
from app.modules.notificaciones import router as notificaciones_router
from app.modules.trazabilidad_metricas import stats_router, router as trazabilidad_router
from app.modules.registro_emergencias import router as registro_router
from app.modules.gestion_atencion import router as gestion_atencion_router
from app.modules.asignacion_inteligente import router as asignacion_router
from app.modules.pagos import router as pagos_router

from app.core.audit_logger import registrar_auditoria
from jose import jwt, JWTError
from app.core.auth import SECRET_KEY, ALGORITHM
from fastapi.staticfiles import StaticFiles
import os

# --- 1. MIDDLEWARE DE AUDITORÍA GLOBAL ---
class AuditoriaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("id")
            except JWTError:
                pass

        path = request.url.path
        method = request.method
        
        # --- FILTRO DE AUDITORÍA REFINADO ---
        es_mutacion = method in ["POST", "PUT", "PATCH", "DELETE"]
        
        # Whitelist: Cosas que SÍ queremos ver aunque sean GET o sean seguridad
        whitelist_seguridad = [
            "/auth/login", 
            "/auth/logout", 
            "/trazabilidad/auditoria", # Quién vigila al vigilante
            "/usuarios/gestionar" 
        ]
        
        # Blacklist: Ruido absoluto (Cosas que se refrescan solas)
        blacklist_ruido = [
            "/notificaciones/unread", 
            "/stats", 
            "/static", 
            "/ws", 
            "/tecnicos/perfil/ubicacion",
            "/trazabilidad/auditoria/cerrar" # Excluir el cierre automático de sesión para evitar spam
        ]

        debe_auditar = es_mutacion or any(path.startswith(r) for r in whitelist_seguridad)
        
        # Si está en la lista negra, no se audita pase lo que pase
        if any(path.startswith(r) for r in blacklist_ruido):
            debe_auditar = False

        if user_id and debe_auditar:
            # --- CAPTURA DE DETALLES DINÁMICOS PRO ---
            params = request.query_params
            monto = params.get("monto") or params.get("monto_recibido")
            metodo = params.get("metodo")
            nombre = params.get("nombre") or params.get("titulo")
            estado = params.get("estado") or params.get("estado_nuevo")
            rol = params.get("rol")
            
            # Identificar el ID del objeto desde la URL (si existe)
            path_parts = [p for p in path.split("/") if p]
            obj_id = path_parts[-1] if path_parts and len(path_parts[-1]) > 1 else ""

            # Construcción del mensaje detallado
            detalle_base = f"Acceso a {path}"
            
            mapeo_nombres = {
                "/auth/login": "Inicio de sesión",
                "/auth/logout": "Cierre de sesión",
                "/usuarios": "Directorio de Usuarios",
                "/talleres": "Catálogo de Talleres",
                "/incidentes": "Emergencia / Incidente",
                "/vehiculos": "Registro de Vehículos",
                "/trazabilidad": "Bitácora / Auditoría",
                "/gestion/pagos": "Operación de Pago",
                "/permisos": "Matriz de Poder"
            }

            entidad = "Registro"
            for key, val in mapeo_nombres.items():
                if path.startswith(key):
                    entidad = val
                    break

            if method == "POST": 
                detalle = f"Creó / Inició {entidad}"
            elif method == "PUT": 
                detalle = f"Actualizó {entidad}"
                if obj_id: detalle += f" (ID: {obj_id})"
            elif method == "DELETE": 
                detalle = f"Eliminó {entidad}"
                if obj_id: detalle += f" (ID: {obj_id})"
            else:
                detalle = f"Consultó {entidad}"

            # Añadir extras si existen
            if nombre: detalle += f": '{nombre}'"
            if rol: detalle += f" [Rol: {rol}]"
            if estado: detalle += f" -> Nuevo Estado: {estado.replace('_', ' ').upper()}"
            if monto: 
                detalle = f"Procesó Pago de Bs. {monto}"
                if metodo: detalle += f" vía {metodo}"

            registrar_auditoria(request, user_id, method, detalle)

        response = await call_next(request)
        return response

# Crear tablas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SOS Automotriz API",
    description="Backend modular basado en Arquitectura de Paquetes (Módulos de Negocio)",
    version="2.0.0"
)

# --- 2. CONFIGURACIÓN DE MIDDLEWARES ---
app.add_middleware(AuditoriaMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/static", StaticFiles(directory="uploads"), name="static")

# --- 3. INCLUSIÓN DE ROUTERS POR MÓDULOS (PAQUETES) ---

# Módulo 2.2.1: Usuarios y Vehículos
app.include_router(auth_router.router)
app.include_router(usuarios_router.router)
app.include_router(vehiculos_router.router)
app.include_router(permisos_router.router)

# Módulo 2.2.6: Gestión de Talleres y Técnicos
app.include_router(talleres_router.router)
app.include_router(tecnicos_router.router)
app.include_router(especialidades_router.router)

# Módulo 2.2.2: Registro de Emergencias
app.include_router(registro_router.router)

# Módulo 2.2.3 & 2.2.7: Gestión y Atención de Solicitudes
app.include_router(gestion_atencion_router.router)

# Módulo 2.2.11 & 2.2.12: Asignación e IA
app.include_router(asignacion_router.router)

# Módulo 2.2.5: Pagos del Cliente
app.include_router(pagos_router.router)

# Módulo 2.2.13: Notificaciones
app.include_router(notificaciones_router.router)

# Módulo 2.2.14: Historial, Trazabilidad y Métricas
app.include_router(stats_router.router)
app.include_router(trazabilidad_router.router)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.get("/")
def read_root():
    return {"message": "SOS Automotriz API - Arquitectura Modular Activada", "status": "Online"}