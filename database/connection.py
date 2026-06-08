import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read Database URL from environment, fallback to a local SQLite database for local test simplicity
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///e:/Antigravity/Advance-Task-Tracker/database/tasktracker.db")

# For SQLite, we need connect_args to allow multithreading, but PostgreSQL doesn't need it
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Set up robust pooling connection settings for enterprise database (PostgreSQL/MySQL etc.)
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
