from sqlalchemy import text
from database.db_config import engine

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM fact_liveflightstatus;
    """))

    count = result.scalar()

print(f"Live API fact rows: {count}")