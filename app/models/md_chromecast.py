from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.config.database import Base

class Chromecast(Base):
    __tablename__ = 'chromecasts'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    mac_address = Column(String, nullable=False)
    uuid = Column(String, nullable=True)

    # Define the relationship to Pair
    pairs = relationship("Pair", back_populates="chromecast")
