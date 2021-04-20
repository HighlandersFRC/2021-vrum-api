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
    deviceId: str
    position: Position
    accuracy: float
    speed: float
    heading: float

class PSM_Pagination(BaseModel):
    psms: List[PSM]


class Path_History_Point(BaseModel):
    position: Position
    timestamp: int
    speed: float
    heading: float


class Token(BaseModel):
    access_token: str
    token_type: str
    token_expires: int


class Vru_Notification(BaseModel):
    id: str
    timestamp: int
    vehiclePsmId: str
    vruPsmId: str
    vruDeviceId: str
    vehicleDeviceId: str
    timeToCollision: float
    distance: float
    reason: str
    pathHistory: List[Path_History_Point]

class PSM_Pagination(BaseModel):
    Vru_Notification: List[Vru_Notification]

