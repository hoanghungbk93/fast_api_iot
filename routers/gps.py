from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import GPSData
from schemas import GPSDataSchema
from pydantic import BaseModel
import random

router = APIRouter(
    prefix="/gps",
    tags=["gps"]
)

class GPSDataRequest(BaseModel):
    latitude: float
    longitude: float

@router.post("/update")
def update_location(data: GPSDataRequest, db: Session = Depends(get_db)):
    gps_data = GPSData(latitude=data.latitude, longitude=data.longitude)
    db.add(gps_data)
    db.commit()
    return {"message": "Location updated successfully"}

@router.get("/location", response_model=GPSDataSchema)
def get_latest_location(db: Session = Depends(get_db)):
    gps_data = db.query(GPSData).order_by(GPSData.timestamp.desc()).first()
    if not gps_data:
        raise HTTPException(status_code=404, detail="No GPS data available")
    return gps_data