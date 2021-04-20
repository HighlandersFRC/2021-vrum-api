from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from schemas import Position, PSM, PSM_Pagination, Token, Vru_Notification
from datetime import datetime, timedelta
import pymongo
import uuid
import hashlib
import json
import math


# Geometry Constants for Geospatial Query
BOUNDING_WIDTH = 1000 # width of bounding rectangle in meters
BOUNDING_HEIGHT = 1000 # height of bounding rectangle in meters
BOUNDING_TIME_MILLIS = 30*1000
M_PER_DEG = 111132.954 #meters per degree latitude
BOUNDING_LAT_OFFSET = (BOUNDING_HEIGHT/2.0)/M_PER_DEG


# Database connection information
key_hash_value = "5e5a634109a9f3e5f759149a4056f262553410fff1aad0f82fb1328a74997d14"
uri = "mongodb://4499-innovation-project:5DlQKCwxEYQvdtBAITOC7w0YPfgtvFbRP96sT6TZNW8Ynyb57SIiMSQ7dzVznJqN7t11CcFPlFKqUIOAh0G4Tw==@4499-innovation-project.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@4499-innovation-project@"
client = pymongo.MongoClient(uri)


# Initialize FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token/")
app = FastAPI()
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ACCESS_TOKEN_EXPIRE_MILLIS = ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000

#Unix Time 0
epoch = datetime.utcfromtimestamp(0)

def unix_time_millis():
    return (datetime.utcnow() - epoch).total_seconds() * 1000.0

def authenticate_key(key):
    try:
        key_hash = str(hashlib.sha256(key.encode()).hexdigest())
        return key_hash == key_hash_value
    except:
        return False

# Deprecated - used only to support /psm routes
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

@app.post("/auth/token/")
async def get_token(form_data: OAuth2PasswordRequestForm = Depends()):
    valid = authenticate_key(form_data.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = Token(
        access_token = str(uuid.uuid4()),
        token_type = "Bearer",
        token_expires = unix_time_millis() + ACCESS_TOKEN_EXPIRE_MILLIS
    )

    mydb = client['test-database']
    mycol = mydb['tokens']
    mycol.insert_one(token.dict())

    return token

async def get_active_token(token: Token = Depends(oauth2_scheme)):
    # Search the database for the supplied Token
    mydb = client['test-database']
    mycol = mydb['tokens']
    query = {"access_token":{"$eq":token}}
    db_token = mycol.find_one(query)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if unix_time_millis() > db_token['token_expires']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return db_token


# Deprecated - Should use new /secure/psm endpoints
@app.get("/psm/")
async def get_psm(request:Request, longitude: float, latitude:float, datetime:int):
    auth_key = request.headers.get("apikey")
    valid = authenticate_key(auth_key)
    if not valid:
        get_correct_response(auth_key)

    mydb = client['test-database']
    mycol = mydb['vru']


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


# Deprecated - Should use new /secure/psm endpoints
@app.post("/psm/")
async def write_psm(request: Request, psm: PSM):
    auth_key = request.headers.get("apikey")
    valid = authenticate_key(auth_key)
    if not valid:
        get_correct_response(auth_key)

    mydb = client['test-database']
    mycol = mydb['vru']
    mycol.insert_one(psm.dict())
    return 200

@app.post("/notifications/")
async def write_notification(notification: Vru_Notification):
    mydb = client['test-database']
    mycol = mydb['notifications']
    mycol.insert_one(notification.dict())
    return 200

@app.get("/secure/psm/")
async def get_psm(longitude: float, latitude:float, datetime:int, token:Token = Depends(get_active_token)):
    mydb = client['test-database']
    mycol = mydb['vru']


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

@app.post("/secure/psm/")
async def write_psm(psm: PSM,token:Token = Depends(get_active_token)):
    mydb = client['test-database']
    mycol = mydb['vru']
    mycol.insert_one(psm.dict())
    return 200

@app.post("/secure/notifications/")
async def write_notification(notification: Vru_Notification, token:Token = Depends(get_active_token)):
    mydb = client['test-database']
    mycol = mydb['notifications']
    mycol.insert_one(notification.dict())
    return 200

@app.get("/count/psm")
async def get_count(token:Token = Depends(get_active_token)):
    mydb = client['test-database']
    mycol = mydb['vru']
    f = {"timestamp":{"$gte":0}}
    
    return mycol.count_documents(f)