from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from sqlalchemy.exc import OperationalError
import time

from database.dependencies import get_db
from database.session import engine
from database.base import Base

from routers.sales import router as sales_router
from routers.products import router as product_router
from routers.inventory import router as inventory_router
from routers.inventory_log import router as inventory_log_router
from routers.sales_read import router as sales_read_router
from routers.auth import router as auth_router
from routers.admin import router as admin_router


import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    for i in range(10):
        try:
            with engine.connect():
                print("Database connected")
            break
        except OperationalError:
            print(f"Database not ready, retry {i+1}/10")
            time.sleep(2)
    else:
        raise RuntimeError("❌ Database never became ready")

    yield


app = FastAPI(
    title="Inventory & Sales Management API",
    version="1.0.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(sales_router)
app.include_router(product_router)
app.include_router(inventory_log_router) #Before inventory router
app.include_router(inventory_router)
app.include_router(sales_read_router)
app.include_router(auth_router)
app.include_router(admin_router)




@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}
