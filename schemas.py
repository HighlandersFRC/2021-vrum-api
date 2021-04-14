from pydantic import BaseModel
from typing import List
from datetime import datetime

class Position(BaseModel):
    lat: float
    lon: float
    elevation: float


class PSM(BaseModel):
    basicType: str
    timestamp: int
    msgCnt: int
    id: str
    position: Position
    accuracy: float
    speed: float
    heading: float


class PSM_Pagination(BaseModel):
    psms: List[PSM]


class Token(BaseModel):
    access_token: str
    token_type: str
    token_expires: int
