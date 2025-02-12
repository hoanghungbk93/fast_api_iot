from pydantic import BaseModel, EmailStr
from models import RoleEnum
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: RoleEnum

class UserLogin(BaseModel):
    username: str
    password: str

class OTPLogin(BaseModel):
    phone_number: str
    otp: str

class Token(BaseModel):
    access_token: str
    token_type: str

class OTPGenerateRequest(BaseModel):
    phone_number: str

class GPSDataSchema(BaseModel):
    id: int
    latitude: float
    longitude: float
    timestamp: datetime

    class Config:
        orm_mode = True
