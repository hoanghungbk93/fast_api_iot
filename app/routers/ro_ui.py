from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from pydantic import BaseModel
import random
from fastapi.responses import FileResponse


router = APIRouter()

class GPSDataRequest(BaseModel):
    latitude: float
    longitude: float

@router.get("/")
async def read_sender():
    return FileResponse("static/views/sender.html")

@router.get("/test")
async def test():
    return FileResponse("static/views/websocket_test.html")

@router.get("/index")
async def index():
    return FileResponse("static/views/index.html")

@router.get("/pairs_history")
async def pairs_history():
    return FileResponse("static/views/pairs.html")