from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database.dependencies import get_db
from database.session import engine
from database.base import Base
from contextlib import asynccontextmanager
from sqlalchemy.exc import OperationalError
import models
import time

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    for i in range(10):  
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database connected, tables created")
            break
        except OperationalError:
            print(f"⏳ Database not ready, retry {i+1}/10")
            time.sleep(2)
    else:
        raise RuntimeError("❌ Database never became ready")

    yield 

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}
            
            
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}
