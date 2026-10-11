from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker, declarative_base
load_dotenv()
DATABASE_URL =os.getenv("DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    client_encoding='utf8',
    connect_args={"options": "-c lc_messages=en_US.UTF-8"}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()