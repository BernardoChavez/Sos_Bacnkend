from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    schemas = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog') AND schema_name NOT LIKE 'pg_toast%'")).fetchall()
    for (schema,) in schemas:
        try:
            conn.execute(text(f"ALTER TABLE {schema}.incidentes ADD COLUMN IF NOT EXISTS cotizacion_monto NUMERIC(10,2);"))
            conn.execute(text(f"ALTER TABLE {schema}.incidentes ADD COLUMN IF NOT EXISTS cotizacion_detalle TEXT;"))
            conn.commit()
            print(f'Migrado esquema {schema}')
        except Exception as e:
            conn.rollback()
            pass
print('Migracion completada')
