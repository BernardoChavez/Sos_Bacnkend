import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import models
from app.core.auth import get_password_hash

def seed_demo_users():
    db = SessionLocal()
    try:
        # Crear Taller
        taller = db.query(models.Taller).filter_by(nombre="Taller Demo").first()
        if not taller:
            taller = models.Taller(
                nombre="Taller Demo",
                razon_social="Demo SRL",
                nit="123456789",
                latitud=-16.5000,
                longitud=-68.1500,
                especialidad="General",
                esta_activo=True
            )
            db.add(taller)
            db.commit()
            db.refresh(taller)

        # Crear Admin Taller
        admin = db.query(models.Usuario).filter_by(email="taller@sos.com").first()
        if not admin:
            admin = models.Usuario(
                nombre="Admin Taller",
                email="taller@sos.com",
                password_hash=get_password_hash("taller123"),
                rol="admin_taller",
                taller_id=taller.id,
                esta_activo=True
            )
            db.add(admin)

        # Crear Técnico
        tecnico = db.query(models.Usuario).filter_by(email="tecnico@sos.com").first()
        if not tecnico:
            tecnico = models.Usuario(
                nombre="Técnico Juan",
                email="tecnico@sos.com",
                password_hash=get_password_hash("tecnico123"),
                rol="tecnico",
                taller_id=taller.id,
                esta_activo=True
            )
            db.add(tecnico)
            db.flush()
            
            tec_profile = models.Tecnico(
                usuario_id=tecnico.id,
                taller_id=taller.id,
                disponible=True,
                especialidad_principal="Mecánica General",
                latitud=-16.5010,
                longitud=-68.1510
            )
            db.add(tec_profile)

        # Crear Cliente
        cliente = db.query(models.Usuario).filter_by(email="cliente@sos.com").first()
        if not cliente:
            cliente = models.Usuario(
                nombre="Cliente Demo",
                email="cliente@sos.com",
                password_hash=get_password_hash("cliente123"),
                rol="cliente",
                esta_activo=True
            )
            db.add(cliente)
            db.flush()

            # Darle un vehículo al cliente
            vehiculo = models.Vehiculo(
                cliente_id=cliente.id,
                marca="Toyota",
                modelo="Corolla",
                placa="123-ABC",
                color="Blanco"
            )
            db.add(vehiculo)

        db.commit()
        print("✅ Usuarios y Taller de demostración creados exitosamente en LOCAL.")
        print("Credenciales:")
        print("Cliente: cliente@sos.com / cliente123")
        print("Taller: taller@sos.com / taller123")
        print("Técnico: tecnico@sos.com / tecnico123")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_users()
