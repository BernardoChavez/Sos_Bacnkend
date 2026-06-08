from app.core.database import engine
from app.models.tenant_models import Base
from sqlalchemy import text

def create_all_schemas():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT schema_name FROM information_schema.schemata"))
        schemas = [r[0] for r in res.fetchall() if r[0] not in ('information_schema', 'pg_catalog', 'pg_toast')]
        
        for schema in schemas:
            print(f"Creating tables in schema: {schema}")
            conn.execute(text(f"SET search_path TO {schema}"))
            Base.metadata.create_all(bind=engine)
        
        conn.commit()
    print("Done!")

if __name__ == "__main__":
    create_all_schemas()
