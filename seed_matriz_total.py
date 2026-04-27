
import sys
import os

# Añadir el directorio raíz al path para poder importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import models

def seed_full_matrix():
    db = SessionLocal()
    try:
        print("🚀 Iniciando siembra de Matriz de Poder Completa...")
        
        # 1. Limpiar permisos previos (opcional, para evitar duplicados)
        db.query(models.RolPermiso).delete()
        db.query(models.Permiso).delete()
        db.commit()

        # ESTRUCTURA: (Modulo, Caso Uso, Accion, Codigo, Roles con permiso por defecto)
        permisos_data = [
            # P1: USUARIOS Y VEHÍCULOS
            ("P1: Usuarios y Vehículos", "CU1: Gestión de Perfil", "Ver", "usuarios.perfil.ver", ['cliente', 'admin_taller', 'tecnico', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU1: Gestión de Perfil", "Modificar", "usuarios.perfil.modificar", ['cliente', 'admin_taller', 'tecnico', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Gestión de Vehículos", "Ver", "usuarios.vehiculos.ver", ['cliente', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Gestión de Vehículos", "Crear", "usuarios.vehiculos.crear", ['cliente', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Gestión de Vehículos", "Modificar", "usuarios.vehiculos.modificar", ['cliente', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Gestión de Vehículos", "Eliminar", "usuarios.vehiculos.eliminar", ['cliente', 'super_admin']),
            
            # P2: REGISTRO DE EMERGENCIAS
            ("P2: Registro Emergencias", "CU12: Solicitar Ayuda", "Ver", "emergencias.ver", ['cliente', 'super_admin']),
            ("P2: Registro Emergencias", "CU12: Solicitar Ayuda", "Solicitar", "emergencias.solicitar", ['cliente', 'super_admin']),
            ("P2: Registro Emergencias", "CU14: Evidencias", "Subir", "emergencias.evidencia.subir", ['cliente', 'super_admin']),
            
            # P4: ATENCIÓN DE SOLICITUDES (TALLER)
            ("P4: Atención Solicitudes", "CU21: Despacho IA", "Ver", "taller.despacho.ver", ['admin_taller', 'super_admin']),
            ("P4: Atención Solicitudes", "CU22: Gestión Servicio", "Aceptar", "taller.servicio.aceptar", ['admin_taller', 'super_admin']),
            ("P4: Atención Solicitudes", "CU22: Gestión Servicio", "Rechazar", "taller.servicio.rechazar", ['admin_taller', 'super_admin']),
            ("P4: Atención Solicitudes", "CU24: Trabajos Técnicos", "Ver", "tecnico.trabajos.ver", ['tecnico', 'super_admin']),
            
            # P7: TRAZABILIDAD Y MÉTRICAS (ADMIN)
            ("P7: Trazabilidad y Métricas", "CU3: Gestión Usuarios", "Ver", "usuarios.gestionar.ver", ['super_admin']),
            ("P7: Trazabilidad y Métricas", "CU3: Gestión Usuarios", "Crear", "usuarios.gestionar.crear", ['super_admin']),
            ("P7: Trazabilidad y Métricas", "CU3: Gestión Usuarios", "Eliminar", "usuarios.gestionar.eliminar", ['super_admin']),
            ("P7: Trazabilidad y Métricas", "CU20: Gestión Talleres", "Ver", "talleres.gestionar.ver", ['super_admin']),
            ("P7: Trazabilidad y Métricas", "CU20: Gestión Talleres", "Crear", "talleres.gestionar.crear", ['super_admin']),
            ("P7: Trazabilidad y Métricas", "Matriz de Poder", "Administrar", "sistema.permisos.gestionar", ['super_admin']),
            ("P7: Trazabilidad y Métricas", "Auditoría", "Ver Bitácora", "sistema.auditoria.ver", ['super_admin']),
        ]

        # Insertar Permisos
        for mod, cu, acc, cod, roles in permisos_data:
            p = models.Permiso(
                modulo=mod,
                caso_uso=cu,
                accion=acc,
                codigo=cod,
                descripcion=f"Permite {acc} en {cu}"
            )
            db.add(p)
            db.flush() # Para obtener el ID

            # Asignar a Roles
            for rol_slug in roles:
                rp = models.RolPermiso(rol=rol_slug, permiso_id=p.id)
                db.add(rp)

        db.commit()
        print("✅ Matriz Completa sembrada con éxito.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_full_matrix()
