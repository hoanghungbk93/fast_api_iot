from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, OTPLogin, OTPGenerateRequest
from auth import hash_password, verify_password, create_access_token
from datetime import timedelta
from auth_manager import AuthManager
from fastapi.responses import RedirectResponse
import logging

logger = logging.getLogger(__name__) 
router = APIRouter(
    prefix="/users",
    tags=["users"]
)

auth_manager = AuthManager()

@router.post("/register/", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registering user: {user.username}")
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        logger.warning(f"Username already registered: {user.username}")
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pwd = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"User registered successfully: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login/", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    access_token = auth_manager.authenticate("password", user.username, user.password, db)
    if not access_token:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login/otp/generate/")
def generate_otp(request: OTPGenerateRequest, db: Session = Depends(get_db)):
    otp = auth_manager.auth_methods["otp"].generate_otp(request.phone_number, db)
    # In a real application, send the OTP via SMS or email
    return {"message": f"OTP sent to {request.phone_number}", "otp": otp}  # Remove "otp" in production

@router.post("/login/otp/", response_model=Token)
def login_otp(otp_login: OTPLogin, db: Session = Depends(get_db)):
    access_token = auth_manager.authenticate("otp", otp_login.phone_number, otp_login.otp, db)
    if not access_token:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Generate JWT token
    token = create_access_token(data={"sub": otp_login.phone_number})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login/google/")
def login_google():
    # Redirect to Google's OAuth2.0 consent screen
    google_auth_url = "https://accounts.google.com/o/oauth2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=email"
    return RedirectResponse(google_auth_url)

@router.get("/login/google/callback/")
def google_callback(request: Request):
    # Extract the authorization code from the request
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    # Exchange the authorization code for an access token
    access_token = auth_manager.authenticate("google", code)
    if not access_token:
        raise HTTPException(status_code=401, detail="Google authentication failed")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/test-error/")
def test_error():
    raise Exception("This is a test exception for Sentry")
