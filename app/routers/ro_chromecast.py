from fastapi import APIRouter, Depends, HTTPException, FastAPI
from sqlalchemy.orm import Session
from app.models.md_chromecast import Chromecast
from app.config.database import get_db
from app.schemas.sch_chromecast import ChromecastCreate, Chromecast as ChromecastSchema
from typing import List
import pychromecast

router = APIRouter(prefix="/chromecasts", tags=["chromecasts"])

app = FastAPI()

@router.get("/chromecasts", response_model=List[ChromecastSchema])
def read_chromecasts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    chromecasts = db.query(Chromecast).offset(skip).limit(limit).all()
    return chromecasts

@router.post("/chromecasts", response_model=ChromecastSchema)
def create_chromecast(chromecast: ChromecastCreate, db: Session = Depends(get_db)):
    db_chromecast = Chromecast(**chromecast.dict())
    db.add(db_chromecast)
    db.commit()
    db.refresh(db_chromecast)
    return db_chromecast

@router.post("/checkout")
async def checkout():
    chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=["101"])
    cast = chromecasts[0]
    cast.wait()
    
    # Disconnect all devices
    cast.quit_app()

    # Clear cache and launch your app
    cast.start_app("com.example.netnamcasting")

    browser.stop_discovery()

    return {"message": "Checkout initiated"}