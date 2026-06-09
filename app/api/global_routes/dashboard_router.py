from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from app.models import global_models, tenant_models
from app.core import database, auth
from datetime import datetime

router = APIRouter(prefix="/dashboard", tags=["Dashboard Operacional Global"])

@router.get("/kpis")
def obtener_kpis_globales(db: Session = Depends(database.get_db),
                          current_user: global_models.Usuario = Depends(auth.check_permissions(["super_admin"]))):
    """Obtiene los KPIs dinámicos calculados a partir de TODOS los esquemas."""
    
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    
    total_incidentes = 0
    total_tecnicos_disponibles = 0
    total_tecnicos = 0
    total_cancelados = 0
    
    asignacion_times = []
    llegada_times = []
    incidentes_por_tipo = {}
    
    try:
        for empresa in empresas:
            if not empresa.schema_name:
                continue
            
            # Cambiar el contexto de la Base de Datos a la empresa actual
            db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
            
            # Contar incidentes activos (pendientes, en_proceso o asignados)
            estados_activos = ['pendiente', 'en_proceso', 'asignado', 'en_camino', 'en_sitio', 'reparando', 'esperando_aprobacion']
            inc_count = db.query(tenant_models.Incidente).filter(tenant_models.Incidente.estado.in_(estados_activos)).count()
            total_incidentes += inc_count
            
            cancelados_count = db.query(tenant_models.Incidente).filter(tenant_models.Incidente.estado == 'cancelado').count()
            total_cancelados += cancelados_count
            
            # Contar técnicos
            techs_disp = db.query(tenant_models.Tecnico).filter(tenant_models.Tecnico.disponible == True).count()
            techs_tot = db.query(tenant_models.Tecnico).count()
            
            total_tecnicos_disponibles += techs_disp
            total_tecnicos += techs_tot
            
            # Recopilar datos reales para tiempos e incidentes por tipo
            todos_inc = db.query(tenant_models.Incidente).all()
            for inc in todos_inc:
                # 1. Incidentes por tipo
                categoria = inc.categoria_ia if inc.categoria_ia else "Otros"
                incidentes_por_tipo[categoria] = incidentes_por_tipo.get(categoria, 0) + 1
                
                # 2. Tiempos usando la bitácora
                if inc.bitacora:
                    bitacora_ordenada = sorted(inc.bitacora, key=lambda b: b.fecha_hora)
                    
                    # Tiempo de asignación (Creación -> Asignado)
                    t_creacion = inc.fecha_creacion
                    t_asignado = next((b.fecha_hora for b in bitacora_ordenada if b.estado_nuevo == 'asignado'), None)
                    if t_asignado and t_creacion:
                        asignacion_times.append((t_asignado - t_creacion).total_seconds())
                        
                    # Tiempo de llegada (En Camino/Asignado -> En Sitio)
                    t_en_camino = next((b.fecha_hora for b in bitacora_ordenada if b.estado_nuevo == 'en_camino'), None)
                    t_en_sitio = next((b.fecha_hora for b in bitacora_ordenada if b.estado_nuevo == 'en_sitio'), None)
                    
                    if t_en_sitio:
                        if t_en_camino:
                            llegada_times.append((t_en_sitio - t_en_camino).total_seconds())
                        elif t_asignado:
                            llegada_times.append((t_en_sitio - t_asignado).total_seconds())
                            
    finally:
        # Asegurarnos siempre de regresar al esquema público por seguridad
        db.execute(text("SET search_path TO public"))
        
    # Calcular promedios matemáticos reales
    avg_asignacion = (sum(asignacion_times) / len(asignacion_times) / 60) if asignacion_times else 0
    avg_llegada = (sum(llegada_times) / len(llegada_times) / 60) if llegada_times else 0
    
    # Formatear KPIs
    asignacion_fmt = round(avg_asignacion, 1)
    llegada_fmt = round(avg_llegada, 1)
    
    return {
        "incidentes_activos": {"valor": total_incidentes, "variacion": "En Tiempo Real", "tendencia": "up"},
        "tecnicos_disponibles": {"disponibles": total_tecnicos_disponibles, "total": total_tecnicos, "estado": "En Servicio"},
        "casos_cancelados": {"valor": total_cancelados, "variacion": "Cancelados o sin atender"},
        "promedio_asignacion": {"valor": asignacion_fmt, "unidad": "m", "estado_sla": "CUMPLIDO" if asignacion_fmt <= 5 else "ATRASADO"},
        "promedio_llegada": {"valor": llegada_fmt, "unidad": "m", "estado_sla": "CUMPLIDO" if llegada_fmt <= 30 else "ATRASADO"},
        "cumplimiento_arribo": {"porcentaje": 92, "texto": "92%"}, # Esto podríamos calcularlo después basándonos en cuantos SLA cumplieron
        "incidentes_por_tipo": [{"nombre": k, "cantidad": v} for k, v in incidentes_por_tipo.items()]
    }

@router.get("/incidentes-recientes")
def obtener_incidentes_recientes(db: Session = Depends(database.get_db),
                                 current_user: global_models.Usuario = Depends(auth.check_permissions(["super_admin"]))):
    """Recorre todos los esquemas y devuelve los 5 incidentes más recientes del sistema completo."""
    empresas = db.query(global_models.Empresa).filter(global_models.Empresa.esta_activa == True).all()
    
    todos_incidentes = []
    
    try:
        for empresa in empresas:
            if not empresa.schema_name:
                continue
            db.execute(text(f"SET search_path TO {empresa.schema_name}, public"))
            
            # Extraer TODOS los incidentes de este esquema particular
            incidentes = db.query(tenant_models.Incidente).order_by(desc(tenant_models.Incidente.fecha_creacion)).all()
            
            for inc in incidentes:
                cliente_nombre = inc.cliente.nombre if inc.cliente else "Desconocido"
                taller_nombre = inc.taller.nombre if inc.taller else "Desconocido"
                
                # CÁLCULO DE SLA: Cronómetro en vivo vs Histórico
                if inc.estado.lower() in ['completado', 'resuelto', 'cancelado']:
                    # Si ya terminó, buscar a qué hora se cerró usando la bitácora
                    if inc.bitacora:
                        # Ordenar bitácora por fecha más reciente y tomar la última
                        ultima_fecha = max(b.fecha_hora for b in inc.bitacora)
                        delta_seconds = (ultima_fecha - inc.fecha_creacion).total_seconds()
                    else:
                        delta_seconds = 0 # Fallback si por error no hay bitácora
                else:
                    # Si sigue activo, el reloj sigue corriendo frente a la hora actual
                    delta_seconds = (datetime.utcnow() - inc.fecha_creacion).total_seconds()
                
                # Determinar colores y bandera del SLA
                if delta_seconds < 300: # < 5 min
                    sla_estado = "CUMPLIDO"
                    sla_color = "blue"
                elif delta_seconds < 600: # < 10 min
                    sla_estado = "RIESGO"
                    sla_color = "orange"
                else: # > 10 min
                    sla_estado = "INCUMPLIDO"
                    sla_color = "red"
                    
                # Formatear el tiempo a String (Ej. 3m 45s)
                mins = int(delta_seconds // 60)
                secs = int(delta_seconds % 60)
                tiempo_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                
                # Acortar el ID (UUID) a 5 caracteres para que no rompa la tabla
                short_id = str(inc.id).split('-')[0].upper()[:5]
                
                todos_incidentes.append({
                    "id": short_id,
                    "cliente": cliente_nombre,
                    "ubicacion": taller_nombre,
                    "taller": "Taller Asignado" if inc.tecnico_id else "IA Asignando...",
                    "sla_estado": sla_estado,
                    "sla_color": sla_color,
                    "tiempo_respuesta": tiempo_str,
                    "fecha": inc.fecha_creacion,
                    "categoria": inc.categoria_ia if inc.categoria_ia else "Otros",
                    "latitud": inc.latitud,
                    "longitud": inc.longitud
                })
                
    finally:
        db.execute(text("SET search_path TO public"))
        
    # Ordenar la lista combinada usando la fecha real y devolver todos los incidentes
    todos_incidentes.sort(key=lambda x: x["fecha"], reverse=True)
    return todos_incidentes


@router.get("/sla-flow")
def obtener_flujo_sla(db: Session = Depends(database.get_db),
                      current_user: global_models.Usuario = Depends(auth.check_permissions(["super_admin"]))):
    """Devuelve las métricas de los hitos del SLA de emergencia."""
    # Como los milestones requieren auditoría detallada de estados, enviaremos datos funcionales
    # alineados al diseño solicitado mientras evoluciona el sistema.
    return [
        {"etapa": "RECEPCIÓN", "porcentaje": 90, "milestone": "100s", "meta": "Aceptación: 120s / Meta 180s"},
        {"etapa": "ASIGNACIÓN IA", "porcentaje": 85, "milestone": "50s", "meta": "Asignación: 80s / Meta 180s"},
        {"etapa": "ACEPTACIÓN TALLER", "porcentaje": 70, "milestone": "70s", "meta": "Aceptación: 120s / Meta 180s"},
        {"etapa": "ARRIBO AL LUGAR", "porcentaje": 40, "milestone": "70s", "meta": "Arribo: 120s / Meta 180s"},
    ]
