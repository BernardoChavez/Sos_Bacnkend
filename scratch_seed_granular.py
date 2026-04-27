from app.core.database import SessionLocal
from app.models import models

def seed_granular_final():
    db = SessionLocal()
    try:
        db.query(models.RolPermiso).delete()
        db.query(models.Permiso).delete()
        db.commit()

        # Todos los roles incluyendo super_admin para que el Admin también sea afectado por la matriz
        # Si quieres que el Admin SIEMPRE pueda todo, añádelo a la lista de cada permiso.
        
        permisos_data = [
            # MODULO 1: USUARIOS Y VEHICULOS
            ("P1: Usuarios y Vehículos", "CU1: Gestión de Perfil", "Ver", "usuarios.perfil.ver", ['cliente', 'admin_taller', 'tecnico', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU1: Gestión de Perfil", "Modificar", "usuarios.perfil.modificar", ['cliente', 'admin_taller', 'tecnico', 'super_admin']),
            
            ("P1: Usuarios y Vehículos", "CU2: Registro Vehículos", "Ver", "usuarios.vehiculos.ver", ['cliente', 'admin_taller', 'tecnico', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Registro Vehículos", "Crear", "usuarios.vehiculos.crear", ['cliente', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Registro Vehículos", "Modificar", "usuarios.vehiculos.modificar", ['cliente', 'super_admin']),
            ("P1: Usuarios y Vehículos", "CU2: Registro Vehículos", "Eliminar", "usuarios.vehiculos.eliminar", ['cliente', 'super_admin']),

            # MODULO 2: REGISTRO DE EMERGENCIAS
            ("P2: Registro Emergencias", "CU12: Solicitar Ayuda", "Solicitar", "emergencias.solicitar", ['cliente', 'super_admin']),
            ("P2: Registro Emergencias", "CU14: Subir Evidencias", "Subir", "emergencias.evidencias", ['cliente', 'super_admin']),

            # MODULO 7: ATENCION DE SOLICITUDES
            ("P7: Atención Solicitudes", "CU21: Panel Despacho", "Ver", "taller.despacho.ver", ['admin_taller', 'super_admin']),
            ("P7: Atención Solicitudes", "CU22: Gestionar Servicio", "Aceptar", "taller.servicio.aceptar", ['admin_taller', 'tecnico', 'super_admin']),
            ("P7: Atención Solicitudes", "CU22: Gestionar Servicio", "Rechazar", "taller.servicio.rechazar", ['admin_taller', 'super_admin']),
            ("P7: Atención Solicitudes", "CU22: Gestionar Servicio", "Asignar Técnico", "taller.servicio.asignar", ['admin_taller', 'super_admin']),

            # MODULO 14: TRAZABILIDAD Y METRICAS (Solo Admin y SuperAdmin)
            ("P14: Trazabilidad", "CU33: Auditoría", "Ver Logs", "sistema.auditoria.ver", ['super_admin']),
            ("P14: Trazabilidad", "CU30: Dashboard", "Ver Métricas", "sistema.stats.ver", ['admin_taller', 'tecnico', 'super_admin']),
        ]

        for mod, cu, acc, cod, roles_permitidos in permisos_data:
            p = models.Permiso(modulo=mod, caso_uso=cu, accion=acc, codigo=cod, descripcion=f"Permite {acc} en {cu}")
            db.add(p)
            db.flush()

            for rol in roles_permitidos:
                db.add(models.RolPermiso(rol=rol, permiso_id=p.id))
        
        db.commit()
        print("✅ Matriz de Permisos sincronizada. Super Admin incluido en la validación.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_granular_final()
