from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from .db import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Doctor")
    hospital_name = Column(String, nullable=True)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)

    age = Column(Float)
    sex = Column(Integer)
    cp = Column(Integer)
    trestbps = Column(Float)
    chol = Column(Float)
    fbs = Column(Integer)
    restecg = Column(Integer)
    thalach = Column(Float)
    exang = Column(Integer)
    oldpeak = Column(Float)
    slope = Column(Integer)
    ca = Column(Integer)
    thal = Column(Integer)

    risk_probability = Column(Float)
    risk_level = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())