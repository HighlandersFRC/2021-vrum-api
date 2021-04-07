from typing import Optional
from fastapi import FastAPI
import pymongo
from datetime import datetime
import uuid
uri = "mongodb://4499-innovation-project:5DlQKCwxEYQvdtBAITOC7w0YPfgtvFbRP96sT6TZNW8Ynyb57SIiMSQ7dzVznJqN7t11CcFPlFKqUIOAh0G4Tw==@4499-innovation-project.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@4499-innovation-project@"
client = pymongo.MongoClient(uri)


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}


@app.post("/user_location/")
def write_item(longitude: float, latitude: float, user_id:int):
    mydb = client['test-database']
    mycol = mydb['Container1']
    event = {
        'vru_id': uuid.uuid4()[:32],
        'Longitude': longitude,
        'latitude': latitude,
        'DateTime': datetime.utcnow()
    }
    mycol.insert_one(event)
    return 200



