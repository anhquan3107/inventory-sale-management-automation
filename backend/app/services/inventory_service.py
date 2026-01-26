from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Sequence

from models.inventory import Inventory
from models.product import Product
from models.inventory_log import InventoryLog
from models.enums.inventory_log_type import InventoryLogType


def init_inventory(
    db: Session,
    product_id: int,
    quantity: int
) -> Inventory:
    if quantity < 0:
        raise ValueError("Initial inventory cannot be negative")

    stmt_product = select(Product).where(Product.id == product_id)
    product = db.execute(stmt_product).scalars().first()

    if not product:
        raise ValueError("Product not found")

    inventory = Inventory(
        product_id=product_id,
        quantity_on_hand=quantity
    )
    db.add(inventory)

    try:
        db.flush()

        log = InventoryLog(
            product_id=product_id,
            change_quantity=quantity,
            quantity_before=0,
            quantity_after=quantity,
            log_type=InventoryLogType.INIT.value,
            reference_id=None
        )
        db.add(log)

        db.commit()
        db.refresh(inventory)
        return inventory

    except IntegrityError:
        db.rollback()
        raise ValueError("Inventory already initialized")


def list_inventory(db: Session) -> Sequence[Inventory]:
    stmt = select(Inventory)
    return db.execute(stmt).scalars().all()


def get_inventory(
    db: Session,
    product_id: int
) -> Inventory | None:
    stmt = select(Inventory).where(
        Inventory.product_id == product_id
    )
    return db.execute(stmt).scalars().first()


def adjust_inventory(
    db: Session,
    product_id: int,
    change_quantity: int,
    log_type: InventoryLogType = InventoryLogType.ADJUSTMENT
) -> Inventory:
    try:
        stmt = (
            select(Inventory)
            .where(Inventory.product_id == product_id)
            .with_for_update()
        )

        inventory = db.execute(stmt).scalars().first()

        if not inventory:
            raise ValueError("Inventory not initialized")

        before_qty = inventory.quantity_on_hand
        after_qty = before_qty + change_quantity

        if after_qty < 0:
            raise ValueError("Inventory cannot be negative")

        inventory.quantity_on_hand = after_qty

        log = InventoryLog(
            product_id=product_id,
            change_quantity=change_quantity,
            quantity_before=before_qty,
            quantity_after=after_qty,
            log_type=log_type.value,
            reference_id=None
        )
        db.add(log)

        db.commit()
        db.refresh(inventory)
        return inventory

    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise
