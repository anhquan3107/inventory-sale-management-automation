from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.dependencies import get_db
from services.inventory_log import get_inventory_logs
from schemas.inventory_log import InventoryLogResponse
from models.enums.inventory_log_type import InventoryLogType

router = APIRouter(prefix="/inventory/logs", tags=["Inventory Logs"])


@router.get("", response_model=list[InventoryLogResponse])
def list_inventory_logs(
    db: Session = Depends(get_db),
    product_id: int | None = Query(default=None),
    log_type: InventoryLogType | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0)
):
    return get_inventory_logs(
        db=db,
        product_id=product_id,
        log_type=log_type,
        limit=limit,
        offset=offset
    )
