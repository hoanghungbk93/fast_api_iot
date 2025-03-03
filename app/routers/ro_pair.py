from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import subprocess
from sqlalchemy.orm import Session
from datetime import datetime
from app.config.database import get_db
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

@router.get("/list", response_model=List[PairSchema])
async def list_pairs(db: Session = Depends(get_db)):
    pairs = db.query(Pair).all()
    return pairs