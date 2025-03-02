import subprocess
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import pychromecast
from app.models.md_chromecast import Chromecast
from app.config.database import get_db
from app.schemas.sch_chromecast import ChromecastCreate, Chromecast as ChromecastSchema
from app.config.utils import get_ip_from_mac
import time


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

    # Sử dụng CastBrowser để tìm Chromecast
    cast_listener = pychromecast.discovery.SimpleCastListener()

    browser = pychromecast.discovery.CastBrowser(cast_listener)
    browser.start_discovery()
    
    time.sleep(3)  # Chờ quét Chromecast
    browser.stop_discovery()

    
    # Lấy danh sách các thiết bị tìm được
    devices = cast_listener.devices
    chromecast_device = next((dev for dev in devices if dev.host == chromecast_ip), None)

    if not chromecast_device:
        raise HTTPException(status_code=404, detail="Chromecast not found on network")

    cast = pychromecast.get_chromecast_from_host((chromecast_ip, 8009))
    cast.wait()

    # Ngắt ứng dụng hiện tại
    cast.quit_app()

    # **ADB CONNECT trước khi chạy lệnh**
    adb_connect_command = f"adb connect {chromecast_ip}:5555"
    adb_run_app_command = f"adb -s {chromecast_ip}:5555 shell monkey -p com.example.netnamcasting -c android.intent.category.LAUNCHER 1"

    try:
        subprocess.run(adb_connect_command, shell=True, check=True)
        time.sleep(2)  # Chờ kết nối ADB
        subprocess.run(adb_run_app_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"ADB command failed: {e}")

    browser.stop_discovery()
    return {"message": f"Checkout initiated for Chromecast {chromecast.code} at {chromecast_ip}"}
