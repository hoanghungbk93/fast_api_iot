from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import subprocess
from sqlalchemy.orm import Session
from datetime import datetime
from app.config.database import get_db
from app.sockets.socket_manager import sio
from app.models.md_chromecast import Chromecast
from app.models.md_pair import Pair
from app.schemas.sch_pair import Pair as PairSchema
from app.config.utils import get_ip_from_mac
from typing import List

router = APIRouter(prefix="/pair", tags=["Pair"])

# Hàm lấy MAC address
def get_mac_address(ip):
    try:
        result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if ip in line:
                return line.split()[2]
    except Exception as e:
        print(f"Error retrieving MAC address for {ip}: {e}")
    return "00:00:00:00:00:00"

@router.post("/verify_code")
async def verify_code(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    code = data.get("code")
    device_ip = request.client.host

    if not code:
        return JSONResponse({"success": False, "message": "No code provided"}, status_code=400)

    # Truy vấn Chromecast bằng ORM
    chromecast = db.query(Chromecast).filter(Chromecast.code == code).first()

    if chromecast:
        chromecast_id, chromecast_mac = chromecast.id, chromecast.mac_address
        chromecast_ip = get_ip_from_mac(chromecast_mac)
        print(f"Handshake successful - Device IP: {device_ip}, Code: {code}, Chromecast IP: {chromecast_ip}")

        # Tạo bản ghi Pair bằng ORM
        mac_address = get_mac_address(device_ip)
        pair_time = datetime.now()  # Use datetime object directly
        new_pair = Pair(
            chromecast_id=chromecast_id,
            ip_address=device_ip,
            mac_address=mac_address,
            pair_time=pair_time
        )
        db.add(new_pair)
        db.commit()
        db.refresh(new_pair)  # Để lấy ID của pair vừa tạo

        # Đếm số kết nối bằng ORM
        connections = db.query(Pair).filter(Pair.chromecast_id == chromecast_id).count()

        # Gửi sự kiện Socket.IO
        await sio.emit("connection_update", {
            "chromecast_ip": chromecast_ip,
            "connections": connections
        })

        return JSONResponse({"success": True, "message": "Connected successfully"})
    else:
        print(f"Invalid code received from IP: {device_ip}")
        return JSONResponse({"success": False, "message": "Invalid code"}, status_code=400)

@router.post("/disconnect")
async def disconnect(request: Request, db: Session = Depends(get_db)):
    device_ip = request.client.host

    # Truy vấn Pair bằng ORM
    pair = db.query(Pair).filter(Pair.ip_address == device_ip).first()

    if pair:
        chromecast_id = pair.chromecast_id
        db.delete(pair)  # Xóa bản ghi Pair
        db.commit()

        # Lấy chromecast_ip bằng ORM
        chromecast = db.query(Chromecast).filter(Chromecast.id == chromecast_id).first()
        chromecast_ip = chromecast.ip_address if chromecast else None

        # Đếm số kết nối còn lại bằng ORM
        connections = db.query(Pair).filter(Pair.chromecast_id == chromecast_id).count()

        print(f"Device disconnected: {device_ip}")
        await sio.emit("connection_update", {
            "chromecast_ip": chromecast_ip,
            "connections": connections
        })

        return JSONResponse({"success": True, "message": "Disconnected successfully"})
    else:
        return JSONResponse({"success": False, "message": "Device not found"}, status_code=404)

@router.get("/list", response_model=List[PairSchema])
async def list_pairs(db: Session = Depends(get_db)):
    pairs = db.query(Pair).all()
    return pairs