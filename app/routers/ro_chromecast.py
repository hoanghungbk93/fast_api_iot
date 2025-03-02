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
    # Chỉ định địa chỉ IP của Chromecast
    chromecast_ip = "10.5.20.85"
    
    # Quét thiết bị Chromecast trên mạng cụ thể
    chromecasts, browser = pychromecast.get_chromecasts(known_hosts=[chromecast_ip])

    # Kiểm tra xem có tìm thấy Chromecast không
    if not chromecasts:
        browser.stop_discovery()
        raise HTTPException(status_code=404, detail="Chromecast not found on eth1.5 (10.5.20.85)")

    cast = chromecasts[0]  # Lấy thiết bị đầu tiên
    cast.wait()

    # Ngắt kết nối ứng dụng hiện tại trên Chromecast
    cast.quit_app()

    # Khởi động lại ứng dụng của bạn
    cast.start_app("com.example.netnamcasting")

    browser.stop_discovery()

    return {"message": "Checkout initiated successfully"}