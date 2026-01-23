from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from services.sales_service import create_sale
from schemas.sales import CreateSaleRequest, CreateSaleResponse


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post(
        "/", 
        summary="Create Sales Order", 
        description="Create a sales order, deduct inventory, and log stock movement atomically",
        response_model=CreateSaleResponse
        )

def create_sale_api(payload: CreateSaleRequest, db: Session = Depends(get_db)):
    try:
        order = create_sale(
            db=db,
            items=[item.model_dump() for item in payload.items],
            sales_channel=payload.sales_channel
        )
        return {
            "order_id": order.id,
            "total_amount": order.total_amount
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

