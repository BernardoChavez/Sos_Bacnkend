from app.core.database import SessionLocal
from sqlalchemy import text

def install_extension():
    db = SessionLocal()
    try:
        print("Instalando extensión uuid-ossp...")
        db.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public;'))
        db.commit()
        print("Éxito! Extensión instalada.")
    except Exception as e:
        db.rollback()
        print("Error instalando extensión:", e)
    finally:
        db.close()

if __name__ == '__main__':
    install_extension()
