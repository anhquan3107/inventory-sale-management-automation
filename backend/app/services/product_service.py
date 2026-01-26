from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Sequence
from models.product import Product


def create_product(
    db: Session,
    data: dict
) -> Product:
    product = Product(**data)
    db.add(product)

    try:
        db.commit()
        db.refresh(product)
        return product

    except IntegrityError:
        db.rollback()
        raise ValueError("SKU already exists")


def get_product(
    db: Session,
    product_id: int
) -> Product | None:
    stmt = select(Product).where(Product.id == product_id)
    return db.execute(stmt).scalars().first()


def list_products(db: Session) -> Sequence[Product]:
    stmt = select(Product)
    return db.execute(stmt).scalars().all()


def update_product(
    db: Session,
    product: Product,
    data: dict
) -> Product:
    try:
        for key, value in data.items():
            setattr(product, key, value)

        db.commit()
        db.refresh(product)
        return product

    except SQLAlchemyError:
        db.rollback()
        raise
