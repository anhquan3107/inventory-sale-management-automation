from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.dependencies import get_db
from models.replenishment import InventoryRecommendation, RecommendationDecision, ReplenishmentPolicy
from schemas.inventory_exceptions import ExceptionClassification, ExceptionMode, InventoryExceptionPage, ReviewStatus
from schemas.replenishment import DecisionRequest, PolicyRequest, RecommendationRequest
from services.forecast_engine import resolve_run
from services.inventory_exceptions import list_exceptions
from services.replenishment import generate_recommendation, policy_dict, put_policy, review_recommendation, serialize_recommendation
from utils.security.bearer import require_admin


router = APIRouter(prefix="/decisions", tags=["Decision Support"])


def require_manager(current_user: dict = Depends(require_admin)):
    return int(current_user["sub"])


def execute(db, fn, *args):
    try:
        return fn(db, *args)
    except (ValueError, IntegrityError) as error:
        db.rollback()
        message = str(error) if isinstance(error, ValueError) else "Conflicting request; reload and retry"
        raise HTTPException(status_code=409, detail=message)


@router.put("/policies/{product_id}")
def update_policy(product_id: int, payload: PolicyRequest, user_id: int = Depends(require_manager),
                  db: Session = Depends(get_db)):
    return execute(db, put_policy, product_id, payload.model_dump())


@router.get("/policies")
def policies(user_id: int = Depends(require_manager), db: Session = Depends(get_db)):
    return [policy_dict(row) for row in db.scalars(select(ReplenishmentPolicy).order_by(ReplenishmentPolicy.product_id))]


@router.post("/generate")
def generate(payload: RecommendationRequest, user_id: int = Depends(require_manager), db: Session = Depends(get_db)):
    return execute(db, generate_recommendation, payload.model_dump(), user_id)


@router.get("/exceptions", response_model=InventoryExceptionPage)
def exceptions(run_id: str = Query(min_length=1, max_length=36),
               mode: ExceptionMode = Query(default="simulation"),
               classification: ExceptionClassification | None = Query(default=None),
               review_status: ReviewStatus | None = Query(default=None),
               limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
               user_id: int = Depends(require_manager), db: Session = Depends(get_db)):
    if not run_id.strip():
        raise HTTPException(status_code=422, detail="Enter a forecast run ID")
    try:
        run = resolve_run(db, run_id.strip())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return list_exceptions(db, run, mode, limit, offset, classification, review_status)


@router.get("/recommendations")
def recommendations(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                    user_id: int = Depends(require_manager), db: Session = Depends(get_db)):
    rows = db.scalars(select(InventoryRecommendation).order_by(InventoryRecommendation.id.desc()).limit(limit).offset(offset))
    return [serialize_recommendation(row, db.scalar(select(RecommendationDecision).where(
        RecommendationDecision.recommendation_id == row.id))) for row in rows]


@router.get("/recommendations/{recommendation_id}")
def recommendation(recommendation_id: int, user_id: int = Depends(require_manager), db: Session = Depends(get_db)):
    row = db.get(InventoryRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    decision = db.scalar(select(RecommendationDecision).where(RecommendationDecision.recommendation_id == row.id))
    return serialize_recommendation(row, decision)


@router.patch("/recommendations/{recommendation_id}")
def review(recommendation_id: int, payload: DecisionRequest, user_id: int = Depends(require_manager),
           db: Session = Depends(get_db)):
    return execute(db, review_recommendation, recommendation_id, payload.model_dump(), user_id)
