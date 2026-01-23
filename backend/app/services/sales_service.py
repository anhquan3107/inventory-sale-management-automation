from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.sales_order import SalesOrder
from models.sales_item import SalesItem
from models.inventory import Inventory
from models.inventory_log import InventoryLog


def create_sale(db: Session, items: list, sales_channel: str):
    """
    items = [
        {"product_id": 1, "quantity": 2, "unit_price": 100},
        ...
    ]
    """

    try:
        # 1️Create sales order
        order = SalesOrder(
            sales_channel=sales_channel,
            total_amount=0
        )
        db.add(order)
        db.flush()  # get order.id without commit

        total_amount = 0

        # Process each item
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            unit_price = item["unit_price"]

            # Check inventory
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product_id
            ).with_for_update().first()

            if not inventory:
                raise ValueError("Inventory not found")

            if inventory.quantity_on_hand < quantity:
                raise ValueError("Not enough stock")

            #  Create sales item
            sales_item = SalesItem(
                sales_order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=quantity * unit_price
            )
            db.add(sales_item)

            # Update inventory
            inventory.quantity_on_hand -= quantity

            # Insert inventory log
            log = InventoryLog(
                product_id=product_id,
                change_quantity=-quantity,
                log_type="SALE",
                reference_id=order.id
            )
            db.add(log)

            total_amount += sales_item.line_total

        # Update order total
        order.total_amount = total_amount

        # Commit everything
        db.commit()

        return order

    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        raise e
