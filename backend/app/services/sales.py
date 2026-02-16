from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal

from models.sales_order import SalesOrder
from models.sales_item import SalesItem
from models.inventory import Inventory
from models.inventory_log import InventoryLog
from models.enums.inventory_log_type import InventoryLogType


def create_sale(
    db: Session,
    items: list[dict],
    sales_channel: str
) -> SalesOrder:
    try:
        order = SalesOrder(
            sales_channel=sales_channel,
            total_amount=Decimal("0.00")
        )
        db.add(order)
        db.flush()

        total_amount = Decimal("0.00")

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            unit_price = item["unit_price"]

            stmt_inventory = (
                select(Inventory)
                .where(Inventory.product_id == product_id)
                .with_for_update()
            )

            inventory = db.execute(stmt_inventory).scalars().first()

            if not inventory:
                raise ValueError("Inventory not found")

            if inventory.quantity_on_hand < quantity:
                raise ValueError("Not enough stock")

            before_qty = inventory.quantity_on_hand
            after_qty = before_qty - quantity

            inventory.quantity_on_hand = after_qty

            sales_item = SalesItem(
                sales_order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=quantity * unit_price
            )
            db.add(sales_item)

            log = InventoryLog(
                product_id=product_id,
                change_quantity=-quantity,
                quantity_before=before_qty,
                quantity_after=after_qty,
                log_type=InventoryLogType.SALE.value,
                reference_id=order.id
            )
            db.add(log)

            total_amount += sales_item.line_total

        order.total_amount = total_amount

        db.commit()
        db.refresh(order)
        return order

    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise
