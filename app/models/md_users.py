from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from app.config.database import Base
from datetime import datetime, timedelta
import enum

class RoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"
    manager = "manager"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(Enum(RoleEnum), default=RoleEnum.user)
    otps = relationship("OTP", back_populates="user")


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(15), index=True)
    otp = Column(String(6))
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(seconds=30))
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="otps")