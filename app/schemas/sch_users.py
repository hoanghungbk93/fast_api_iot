from pydantic import BaseModel, EmailStr
from app.models.md_users import RoleEnum
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