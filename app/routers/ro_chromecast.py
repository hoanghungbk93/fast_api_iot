import subprocess
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import pychromecast
from app.models.md_chromecast import Chromecast
from app.config.database import get_db
from app.schemas.sch_chromecast import ChromecastCreate, Chromecast as ChromecastSchema
from app.config.utils import get_ip_from_mac

router = APIRouter(prefix="/chromecasts", tags=["chromecasts"])


@router.get("/", response_model=List[ChromecastSchema])
def read_chromecasts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Chromecast).offset(skip).limit(limit).all()

@router.post("/", response_model=ChromecastSchema)
def create_chromecast(chromecast: ChromecastCreate, db: Session = Depends(get_db)):
    db_chromecast = Chromecast(**chromecast.dict())
    db.add(db_chromecast)
    db.commit()
    db.refresh(db_chromecast)
    return db_chromecast

@router.delete("/{chromecast_id}")
def delete_chromecast(chromecast_id: int, db: Session = Depends(get_db)):
    db_chromecast = db.query(Chromecast).filter(Chromecast.id == chromecast_id).first()
    if not db_chromecast:
        raise HTTPException(status_code=404, detail="Chromecast not found")
    db.delete(db_chromecast)
    db.commit()
    return {"message": "Chromecast deleted"}

@router.post("/checkout")
async def checkout(chromecast_id: int, db: Session = Depends(get_db)):
    """API nhận ID của Chromecast từ client"""
    # Lấy thông tin Chromecast từ DB theo ID
    chromecast = db.query(Chromecast).filter(Chromecast.id == chromecast_id).first()

    if not chromecast:
        raise HTTPException(status_code=404, detail="Chromecast not found")

    # Lấy IP từ MAC Address
    chromecast_ip = get_ip_from_mac(chromecast.mac_address)

    # Quét thiết bị Chromecast
    chromecasts, browser = pychromecast.get_chromecasts(known_hosts=[chromecast_ip])

    if not chromecasts:
        browser.stop_discovery()
        raise HTTPException(status_code=404, detail="Chromecast not found on network")

    cast = chromecasts[0]
    cast.wait()
    cast.quit_app()

    # Chạy lệnh ADB để mở app
    subprocess.run(["adb", "connect", f"{chromecast_ip}:5555"], check=True)
    subprocess.run(["adb", "-s", f"{chromecast_ip}:5555", "shell", "monkey", "-p", "com.example.netnamcasting", "-c", "android.intent.category.LAUNCHER", "1"], check=True)

    browser.stop_discovery()
    return {"message": f"Checkout initiated for Chromecast {chromecast.code} at {chromecast_ip}"}
