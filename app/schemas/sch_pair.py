from pydantic import BaseModel
from datetime import datetime

class PairBase(BaseModel):
    chromecast_id: int
    ip_address: str
    mac_address: str
    pair_time: datetime
    active: bool

class PairCreate(PairBase):
    pass

class Pair(PairBase):
    id: int

    class Config:
        from_attributes = True
