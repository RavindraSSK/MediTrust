from sqlalchemy import Column, Integer, String, Float
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