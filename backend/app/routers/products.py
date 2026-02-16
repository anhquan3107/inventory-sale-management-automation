from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from schemas.products import (
    CreateProductRequest,
    UpdateProductRequest,
    ProductResponse
)
from services.product import (
    create_product,
    get_product,
    list_products,
    update_product
)

router = APIRouter(prefix="/products", tags=["Products"])

@router.post(
    "/",
    response_model=ProductResponse,
    summary="Create product"
)
def create_product_api(
    payload: CreateProductRequest,
    db: Session = Depends(get_db)
):
    try:
        product = create_product(db, payload.model_dump())
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/",
    response_model=list[ProductResponse],
    summary="List products"
)
def list_products_api(db: Session = Depends(get_db)):
    return list_products(db)

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product detail"
)
def get_product_api(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product"
)
def update_product_api(
    product_id: int,
    payload: UpdateProductRequest,
    db: Session = Depends(get_db)
):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    updated = update_product(
        db,
        product,
        payload.model_dump(exclude_unset=True)
    )
    return updated
