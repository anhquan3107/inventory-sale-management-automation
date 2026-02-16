from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database.dependencies import get_db
from services.sales_read import list_sales, get_sale_detail
from schemas.sales_read import SaleRead, SaleDetailRead

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get(
    "",
    response_model=list[SaleRead],
    summary="List sales for dashboard"
)
def list_sales_api(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sales_channel: str | None = Query(default=None),
    product_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_sales(
        db=db,
        date_from=date_from,
        date_to=date_to,
        sales_channel=sales_channel,
        product_id=product_id,
    )


@router.get(
    "/{order_id}",
    response_model=SaleDetailRead,
    summary="Get sale detail"
)
def get_sale_detail_api(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = get_sale_detail(db=db, order_id=order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Sale not found")

    return order
