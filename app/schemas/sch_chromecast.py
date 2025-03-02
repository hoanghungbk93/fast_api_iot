from pydantic import BaseModel

class ChromecastBase(BaseModel):
    code: str
    mac_address: str
    uuid: str
class ChromecastCreate(ChromecastBase):
    pass

class Chromecast(ChromecastBase):
    id: int

    class Config:
        from_attributes = True