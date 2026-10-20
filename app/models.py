from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = "sqlite:////data/freetime.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    balance = Column(Float, default=5.0)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    year = Column(Integer)
    genre = Column(String)
    stock = Column(Integer, default=3)
    rental_price = Column(Float, default=2.0)
    rating = Column(String, default="PG")


class Snack(Base):
    __tablename__ = "snacks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer, default=100)


class Rental(Base):
    __tablename__ = "rentals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_id = Column(Integer, ForeignKey("movies.id"))
    qty = Column(Integer, default=1)
    rented_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    import os
    os.makedirs("/data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
