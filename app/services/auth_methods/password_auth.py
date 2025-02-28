from app.services.auth_methods.base_auth import BaseAuth
from app.services.auth_methods.auth import verify_password, create_access_token
from sqlalchemy.orm import Session
from app.models.md_users import User

class PasswordAuth(BaseAuth):
    def authenticate(self, username: str, password: str, db: Session):
        db_user = db.query(User).filter(User.username == username).first()
        if not db_user or not verify_password(password, db_user.hashed_password):
            return None
        return create_access_token(data={"sub": username}) 