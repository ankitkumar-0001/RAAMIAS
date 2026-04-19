from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    is_online = Column(Boolean, default=False)


class Blacklist(Base):
    __tablename__ = "blacklist"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    banned_at = Column(DateTime, default=datetime.datetime.utcnow)
