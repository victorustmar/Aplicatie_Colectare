from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
import json

# Example .env:
# DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/appdb?charset=utf8mb4"

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    json_serializer=json.dumps,
    json_deserializer=json.loads,   # <-- this makes JSON columns come back as dicts
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
