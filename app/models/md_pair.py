from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.config.database import Base
from datetime import datetime

class Pair(Base):
    __tablename__ = 'pairs'
    id = Column(Integer, primary_key=True, index=True)
    chromecast_id = Column(Integer, ForeignKey('chromecasts.id'), nullable=False)
    ip_address = Column(String, nullable=False)
    mac_address = Column(String, nullable=False)
    pair_time = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

    chromecast = relationship("Chromecast", back_populates="pairs")
