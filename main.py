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

BOUNDING_HEIGHT = 1000 #km
BOUNDING_WIDTH = 1000 #km
BOUNDING_TIME_MILLIS = 30*1000


M_PER_DEG = 111132.954 

BOUNDING_LAT_OFFSET = (BOUNDING_HEIGHT/2.0)/M_PER_DEG

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


    #Compute minimum and maximum time ranges
    start_millis = datetime - BOUNDING_TIME_MILLIS
    end_millis = datetime + BOUNDING_TIME_MILLIS

    #compute bounding latitudes
    north_bound = latitude + BOUNDING_LAT_OFFSET
    south_bound = latitude - BOUNDING_LAT_OFFSET

    #compute bounding longitudes based on center latitude
    long_offset = ((BOUNDING_WIDTH/2.0) / (M_PER_DEG*math.cos(math.radians(latitude))))
    east_bound = longitude + long_offset
    west_bound = longitude - long_offset

    query = {"$and":[
        {"timestamp": {"$gte": start_millis}},
        {"timestamp": {"$lte": end_millis}},
        {"position.lat": {"$gte": south_bound}},
        {"position.lat": {"$lte": north_bound}},
        {"position.lon": {"$gte": west_bound}},
        {"position.lon": {"$lte": east_bound}}
    ]}

    #restructures mongo result into psm pagination
    psms = mycol.find(query)
    psm_list = []
    for x in psms:
        psm_list.append(x)

    psm_response = PSM_Pagination(psms = psm_list)
    return psm_response