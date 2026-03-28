from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    # 🚀 Notice: No password column! AWS handles that now.
    is_online = Column(Boolean, default=False)
