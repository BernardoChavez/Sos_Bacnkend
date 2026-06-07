from app.core.database import SessionLocal
from sqlalchemy import text

def test():
    db = SessionLocal()
    try:
        print("Executing create_tenant_schema...")
        db.execute(text("SELECT create_tenant_schema('tenant_test123')"))
        db.commit()
        print("Success!")
    except Exception as e:
        db.rollback()
        print("Error executing function:", e)
    finally:
        db.close()

if __name__ == '__main__':
    test()
