from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from schemas.inventory import (
    InventoryInitRequest,
    InventoryAdjustRequest,
    InventoryResponse
)
from services.inventory import (
    init_inventory,
    list_inventory,
    get_inventory,
    adjust_inventory
)
router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.post(
    "/init",
    response_model=InventoryResponse,
    summary="Initialize inventory for product"
)
def init_inventory_api(
    payload: InventoryInitRequest,
    db: Session = Depends(get_db)
):
    try:
        inventory = init_inventory(
            db,
            payload.product_id,
            payload.quantity
        )
        return inventory
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/",
    response_model=list[InventoryResponse],
    summary="List inventory"
)
def list_inventory_api(db: Session = Depends(get_db)):
    return list_inventory(db)

@router.get(
    "/{product_id}",
    response_model=InventoryResponse,
    summary="Get inventory by product"
)
def get_inventory_api(
    product_id: int,
    db: Session = Depends(get_db)
):
    inventory = get_inventory(db, product_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory

@router.put(
    "/adjust",
    response_model=InventoryResponse,
    summary="Adjust inventory manually"
)
def adjust_inventory_api(
    payload: InventoryAdjustRequest,
    db: Session = Depends(get_db)
):
    try:
        inventory = adjust_inventory(
            db,
            payload.product_id,
            payload.change_quantity
        )
        return inventory
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
