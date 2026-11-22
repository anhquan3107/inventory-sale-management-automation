import { isAxiosError } from 'axios'
import axios from './axios'
import { API_PATHS } from './paths'
import type {
  DecisionRequest,
  ForecastAccuracy,
  ForecastPrediction,
  ForecastRun,
  PolicyValues,
  Recommendation,
  RecommendationRequest,
  ReplenishmentPolicy,
  SalesCoverage,
  SalesCoverageValues,
  WeeklyForecast,
} from '../types/replenishment'

const { DECISIONS, FORECAST } = API_PATHS

export const replenishmentApi = {
  async policies() {
    return (await axios.get<ReplenishmentPolicy[]>(DECISIONS.POLICIES)).data
  },
  async savePolicy(productId: number, values: PolicyValues) {
    return (await axios.put<ReplenishmentPolicy>(DECISIONS.POLICY(productId), values)).data
  },
  async coverage() {
    return (await axios.get<SalesCoverage[]>(FORECAST.COVERAGE)).data
  },
  async saveCoverage(productId: number, values: SalesCoverageValues) {
    return (await axios.put<SalesCoverage>(FORECAST.PRODUCT_COVERAGE(productId), {
      ...values,
      confirms_complete_sales: true,
    })).data
  },
  async generateForecast(productId: number, reviewDate: string, protectionWeeks: number) {
    const { data } = await axios.post<ForecastRun>(FORECAST.GENERATE, {
      product_ids: [productId],
      as_of_date: reviewDate,
      weekly_horizon: protectionWeeks,
    })
    return data.run_id
  },
  async weeklyForecast(productId: number, runId?: string): Promise<WeeklyForecast> {
    const { data } = await axios.get<ForecastRun & { items: ForecastAccuracy[] }>(
      FORECAST.ACCURACY,
      { params: { granularity: 'weekly', run_id: runId } },
    )
    const { data: predictions } = await axios.get<{ items: ForecastPrediction[] }>(
      FORECAST.PREDICTIONS,
      { params: { granularity: 'weekly', run_id: data.run_id, product_id: productId } },
    )
    return {
      run_id: data.run_id,
      generated_at: data.generated_at,
      as_of_date: data.as_of_date,
      accuracy: data.items.find((item) => item.product_id === productId),
      predictions: predictions.items,
    }
  },
  async generateRecommendation(request: RecommendationRequest) {
    return (await axios.post<Recommendation>(DECISIONS.GENERATE, request)).data
  },
  async recommendations(limit: number, offset: number) {
    return (await axios.get<Recommendation[]>(DECISIONS.RECOMMENDATIONS, {
      params: { limit, offset },
    })).data
  },
  async recommendation(id: number) {
    return (await axios.get<Recommendation>(DECISIONS.RECOMMENDATION(id))).data
  },
  async review(id: number, request: DecisionRequest) {
    return (await axios.patch<Recommendation>(DECISIONS.RECOMMENDATION(id), request)).data
  },
}

type ValidationDetail = { loc?: (string | number)[]; msg?: string }

export function decisionError(error: unknown, fallback: string) {
  if (!isAxiosError<{ detail?: string | ValidationDetail[] }>(error)) return fallback

  const detail = error.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const messages = detail.flatMap(({ loc, msg }) => {
      if (!msg) return []
      const field = loc?.slice(1).join(' ').replaceAll('_', ' ')
      return [field ? `${field}: ${msg}` : msg]
    })
    if (messages.length) return messages.join('. ')
  }
  return fallback
}
