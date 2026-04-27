import sys
import os

# Añadir el directorio raíz al path para poder importar app
sys.path.append(os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))

from app.core.database import SessionLocal
from app.models import models

def limpiar_auditoria():
    db = SessionLocal()
    try:
        print("Iniciando limpieza de la tabla de auditoria...")
        num_borrados = db.query(models.Auditoria).delete()
        db.commit()
        print(f"Exito: Se han eliminado {num_borrados} registros de auditoria.")
        print("Sistema optimizado.")
    except Exception as e:
        db.rollback()
        print(f"Error al limpiar auditoria: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    limpiar_auditoria()
