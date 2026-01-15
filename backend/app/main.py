from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.db.dependencies import get_db

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
            
            
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}
