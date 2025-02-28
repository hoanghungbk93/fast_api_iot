from sqlalchemy import Column, Integer, String, Float, DateTime
from app.config.database import Base
from datetime import datetime

class GPSData(Base):
    __tablename__ = 'gps_data'
    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
