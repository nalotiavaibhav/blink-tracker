from sqlalchemy import create_engine, text

# Your RDS Postgres URL
db_url = "postgresql://waw_admin:waw_admin_12@waw-database-2.chu0quwccas2.ap-south-1.rds.amazonaws.com:5432/waw_test"

# Create engine
engine = create_engine(db_url, echo=True)  # echo=True shows SQL logs

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Connection successful:", result.scalar())
except Exception as e:
    print("❌ Connection failed:", e)
