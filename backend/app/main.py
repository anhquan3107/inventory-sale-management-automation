from fastapi import FastAPI, Depends
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


import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    for i in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database connected, tables created")
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

app.include_router(sales_router)
app.include_router(product_router)
app.include_router(inventory_log_router) #Before inventory router
app.include_router(inventory_router)
app.include_router(sales_read_router)
app.include_router(auth_router)




@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}
