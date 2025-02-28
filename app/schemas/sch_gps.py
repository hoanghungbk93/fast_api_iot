from pydantic import BaseModel
from datetime import datetime

class GPSDataSchema(BaseModel):
    id: int
    latitude: float
    longitude: float
    timestamp: datetime

    class Config:
        from_attributes = True