from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.dependencies import get_db
from models.enums.user_role import UserRole
from schemas.forecast import (
    ForecastAccuracyListResponse,
    ForecastGenerationResponse,
    ForecastPredictionListResponse,
    GenerateForecastRequest,
)
from services.forecast_engine import (
    generate_forecast_run,
    list_forecast_accuracy,
    list_forecast_predictions,
)
from utils.security.bearer import require_auth


router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.post(
    "/generate",
    response_model=ForecastGenerationResponse,
    summary="Generate weekly and monthly demand forecasts",
)
def generate_forecast(
    payload: GenerateForecastRequest,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if current_user["role"] != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        return generate_forecast_run(
            db=db,
            generated_by_user_id=int(current_user["sub"]),
            weekly_horizon=payload.weekly_horizon,
            monthly_horizon=payload.monthly_horizon,
            product_ids=payload.product_ids,
        )
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
