export interface PolicyValues {
  lead_time_weeks: number
  review_interval_weeks: number
  safety_stock: number
  minimum_order_quantity: number
  pack_size: number
}

export interface ReplenishmentPolicy extends PolicyValues {
  product_id: number
  version: number
}

export interface SalesCoverageValues {
  observed_from: string
  observed_through: string
  source: string
  dataset_version: string
  configuration: Record<string, unknown>
}

export interface SalesCoverage extends SalesCoverageValues {
  product_id: number
}

export interface ForecastRun {
  run_id: string
  generated_at: string
  as_of_date: string | null
}

export interface ForecastAccuracy {
  product_id: number
  selected_model: string
  training_points: number
  mae: string | null
  details: { status?: string; dataset_version?: string | null } | null
}

export interface ForecastPrediction {
  horizon_step: number
  period_start: string
  predicted_quantity: string
}

export interface WeeklyForecast extends ForecastRun {
  accuracy?: ForecastAccuracy
  predictions: ForecastPrediction[]
}

export interface SimulatedReceipt {
  arrival_week: number
  quantity: number
}

export type RecommendationMode = 'simulation' | 'live'

export interface RecommendationRequest {
  request_key: string
  run_id: string
  product_id: number
  mode: RecommendationMode
  simulated_on_hand?: number
  simulated_receipts?: SimulatedReceipt[]
  confirms_no_incoming_orders?: boolean
}

export type DecisionAction = 'approved' | 'modified' | 'rejected'
export type ReviewStatus = 'pending' | DecisionAction

export interface DecisionRequest {
  action: DecisionAction
  quantity?: number
  reason?: string
}

export interface RecommendationDecision {
  action: DecisionAction
  quantity: number
  reason: string | null
  user_id: number
  created_at: string
}

export type RecommendationDiagnostics = { rules_version: string } & (
  | { status: 'unsupported_snapshot' }
  | {
    status: 'available'
    first_shortage_step: number | null
    first_shortage_period_start: string | null
    first_shortage_quantity: string | null
    maximum_projected_deficit: string
    shortage_during_lead_time: boolean
    excess_stock_review: boolean
    excess_stock_factor: string
    excess_stock_threshold: string | null
    excess_above_review_threshold: string | null
    zero_demand_stock_review: boolean
  }
)

export type ExceptionClassification = 'shortage_within_lead_time' | 'shortage_after_lead_time'
  | 'planned_replenishment' | 'excess_stock_review' | 'insufficient_evidence' | 'not_generated'
  | 'unsupported_snapshot' | 'no_exception'

export interface ExceptionScope {
  run_id: string
  mode: RecommendationMode
}

export interface ExceptionQuery extends ExceptionScope {
  classification?: ExceptionClassification
  review_status?: ReviewStatus
  limit: number
  offset: number
}

export interface InventoryException {
  product_id: number
  sku: string
  product_name: string
  product_active: boolean
  recommendation_id: number | null
  review_status: ReviewStatus | null
  classification: ExceptionClassification
  first_shortage_period_start: string | null
  first_shortage_quantity: string | null
  excess_stock_review: boolean | null
  zero_demand_stock_review: boolean | null
  suggested_quantity: number | null
  reasons: string[]
}

export interface InventoryExceptionPage extends ExceptionScope {
  as_of_date: string | null
  rules_version: string
  total: number
  scope_total: number
  missing_recommendations: number
  items: InventoryException[]
}

export interface Recommendation {
  id: number
  product_id: number
  suggested_quantity: number
  action: 'reorder' | 'no_action'
  status: ReviewStatus
  created_at: string
  created_by_user_id: number
  decision: RecommendationDecision | null
  snapshot: {
    request: RecommendationRequest
    policy: ReplenishmentPolicy
    on_hand: number
    decision_date: string
    mode: RecommendationMode
    forecast: { period_start: string; quantity: string }[]
    diagnostics?: RecommendationDiagnostics
    model: string
    dataset_version: string | null
    result: {
      inventory_position: number
      protection_weeks: number
      lead_time_demand: string
      protection_demand: string
      target_stock: string
      stockout_risk: boolean
      projected_week_end_stock: string[]
    }
  }
}
