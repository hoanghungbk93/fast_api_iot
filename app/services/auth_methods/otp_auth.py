from app.services.auth_methods.base_auth import BaseAuth
from sqlalchemy.orm import Session
from app.models.md_users import OTP
import random
from datetime import datetime, timedelta, timezone

class OTPAuth(BaseAuth):
    def generate_otp(self, phone_number: str, db: Session):
        otp = random.randint(100000, 999999)
        otp_entry = OTP(
            phone_number=phone_number,
            otp=str(otp),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=30)
        )
        db.add(otp_entry)
        db.commit()
        return otp

    def authenticate(self, phone_number: str, otp: str, db: Session):
        otp_entry = db.query(OTP).filter(OTP.phone_number == phone_number, OTP.otp == otp).first()
        if not otp_entry or otp_entry.expires_at < datetime.utcnow():
            return None

        db.delete(otp_entry)
        db.commit()
        return "access_token"  # Replace with actual token generation logic 