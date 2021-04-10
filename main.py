from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status
import pymongo
from datetime import datetime
from pydantic import BaseModel
from typing import List
import uuid
import hashlib
import json
import math

key_hash_value = "5e5a634109a9f3e5f759149a4056f262553410fff1aad0f82fb1328a74997d14"

uri = "mongodb://4499-innovation-project:5DlQKCwxEYQvdtBAITOC7w0YPfgtvFbRP96sT6TZNW8Ynyb57SIiMSQ7dzVznJqN7t11CcFPlFKqUIOAh0G4Tw==@4499-innovation-project.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@4499-innovation-project@"
client = pymongo.MongoClient(uri)
app = FastAPI()

BOUNDING_HEIGHT = 1.0 #km
BOUNDING_WIDTH = 1.0 #km

BOUNDING_LAT_OFFSET = (BOUNDING_HEIGHT/2.0)/111.132954 

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

#"https://vrum-rest.api.azurewebsites.net"
def authenticate_key(key):
    try:
        key_hash = str(hashlib.sha256(key.encode()).hexdigest())
        return key_hash == key_hash_value
    except:
        return False


def get_correct_response(auth_key):
    if not auth_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication key was specified. If you have a key, please add auth_key: **authentication_key** to your " +
            f"request header",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication key",
        )


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}


@app.post("/user_location/")
def write_item(request: Request, longitude: float, latitude: float, user_id: int):
    auth_key = request.headers.get("apikey")
    valid = authenticate_key(auth_key)
    if not valid:
        get_correct_response(auth_key)

    mydb = client['test-database']
    mycol = mydb['Container1']
    event = {
        'id': user_id,
        'vru_id': str(uuid.uuid4())[:32],
        'Longitude': longitude,
        'latitude': latitude,
        'DateTime': datetime.utcnow()
    }
    mycol.insert_one(event)
    return 200


@app.post("/psm/")
def write_psm(request: Request, psm: PSM):
    auth_key = request.headers.get("apikey")
    valid = authenticate_key(auth_key)
    if not valid:
        get_correct_response(auth_key)

    mydb = client['test-database']
    mycol = mydb['Container1']
    mycol.insert_one(psm.dict())
    return 200


@app.get("/psm/")
def get_psm(request:Request, longitude: float, latitude:float, datetime:int):
    auth_key = request.headers.get("apikey")
    valid = authenticate_key(auth_key)
    if not valid:
        get_correct_response(auth_key)

    mydb = client['test-database']
    mycol = mydb['Container1']

    start_millis = datetime - 30000
    end_millis = datetime + 30000

    north_bound = latitude + BOUNDING_LAT_OFFSET
    south_bound = latitude - BOUNDING_LAT_OFFSET

    long_offset = ((BOUNDING_WIDTH/2.0) / (40075.0*math.cos(math.radians(latitude)/360.0)))
    east_bound = longitude + long_offset
    west_bound = longitude - long_offset

    #{'_id': ObjectId('6071f813cf575f480ecbc485'), 'basicType': 'aPEDESTRIAN', 'timestamp': 1618081809268, 'msgCnt': 1, 'id': '795c1fec-6ad7-4ce8-8506-490b29e8e5f8', 'position': {'lat': 40.4737417, 'lon': -104.9694426, 'elevation': 1493.5211130532612}, 'accuracy': 5.914999961853027, 'speed': 0.00041544949635863304, 'heading': 177.62246704101562}

    query = {"$and":[
        {"timestamp": {"$gte": start_millis}},
        {"timestamp": {"$lte": end_millis}},
        {"position.lat": {"$gte": south_bound}},
        {"position.lat": {"$lte": north_bound}},
        {"position.lon": {"$gte": west_bound}},
        {"position.lon": {"$lte": east_bound}}
    ]}

    psms = mycol.find(query)
    psm_list = []
    for x in psms:
        psm_list.append(x)

    psm_response = PSM_Pagination(psms = psm_list)
    return psm_response