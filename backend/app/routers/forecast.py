from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from database.dependencies import get_db
from schemas.forecast import (
    ForecastAccuracyListResponse,
    ForecastGenerationResponse,
    ForecastPredictionListResponse,
    GenerateForecastRequest,
    CoverageRequest,
)
from services.forecast_engine import (
    generate_forecast_run,
    list_forecast_accuracy,
    list_forecast_predictions,
    list_backtest_points,
)
from models.forecast_evidence import ForecastCoverage
from models.product import Product
from utils.security.bearer import require_admin, require_auth


router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.post(
    "/generate",
    response_model=ForecastGenerationResponse,
    summary="Generate weekly and monthly demand forecasts",
)
def generate_forecast(
    payload: GenerateForecastRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return generate_forecast_run(
            db=db,
            generated_by_user_id=int(current_user["sub"]),
            weekly_horizon=payload.weekly_horizon,
            monthly_horizon=payload.monthly_horizon,
            product_ids=payload.product_ids,
            as_of_date=payload.as_of_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.put("/coverage/{product_id}", summary="Declare a continuous, complete sales observation window")
def put_coverage(product_id: int, payload: CoverageRequest,
                 current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.scalar(select(Product).where(Product.id == product_id).with_for_update()):
        raise HTTPException(status_code=404, detail="Product not found")
    row = db.get(ForecastCoverage, product_id)
    values = payload.model_dump(exclude={"confirms_complete_sales"})
    if row:
        if all(getattr(row, key) == value for key, value in values.items()):
            return {"product_id": product_id, **values}
        if row.dataset_version == payload.dataset_version:
            raise HTTPException(status_code=409, detail="Changed coverage requires a new dataset_version")
        for key, value in values.items():
            setattr(row, key, value)
    else:
        db.add(ForecastCoverage(product_id=product_id, **values))
    db.commit()
    return {"product_id": product_id, **values}


@router.get("/coverage")
def get_coverage(current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    return [{column.name: getattr(row, column.name) for column in ForecastCoverage.__table__.columns}
            for row in db.scalars(select(ForecastCoverage).order_by(ForecastCoverage.product_id))]


@router.get("/backtest-points")
def get_backtest_points(run_id: str, product_id: int = Query(ge=1),
                       granularity: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
                       limit: int = Query(default=500, ge=1, le=2000), offset: int = Query(default=0, ge=0),
                       current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        return list_backtest_points(db, run_id, product_id, granularity, limit, offset)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/predictions",
    response_model=ForecastPredictionListResponse,
    summary="Get forecast predictions for a run",
)
def get_forecast_predictions(
    granularity: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    run_id: str | None = Query(default=None),
    product_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        return list_forecast_predictions(
            db=db,
            granularity=granularity,
            run_id=run_id,
            product_id=product_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/accuracy",
    response_model=ForecastAccuracyListResponse,
    summary="Get forecast accuracy metrics for a run",
)
def get_forecast_accuracy(
    granularity: str = Query(default="weekly", pattern="^(weekly|monthly)$"),
    run_id: str | None = Query(default=None),
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        return list_forecast_accuracy(
            db=db,
            granularity=granularity,
            run_id=run_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
