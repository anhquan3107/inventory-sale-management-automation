from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.product import Product

def create_product(db: Session, data: dict) -> Product:
    product = Product(**data)
    db.add(product)

    try:
        db.commit()
        db.refresh(product)
        return product
    except IntegrityError:
        db.rollback()
        raise ValueError("SKU already exists")

def get_product(db: Session, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id).first()

def list_products(db: Session) -> list[Product]:
    return db.query(Product).all()

def update_product(
    db: Session,
    product: Product,
    data: dict
) -> Product:
    for key, value in data.items():
        setattr(product, key, value) #setattr(product, "unit_price", 1099)

    db.commit()
    db.refresh(product)
    return product
