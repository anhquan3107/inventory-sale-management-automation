import type { WeeklyForecast } from '../../types/replenishment'

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 })
const dayFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})
const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const models: Record<string, string> = {
  naive: 'Naive',
  moving_average: 'Moving average',
  exponential_smoothing: 'Exponential smoothing',
  unavailable: 'Unavailable',
}

export const todayUtc = () => new Date().toISOString().slice(0, 10)
export const dateAtUtc = (day: string) => new Date(`${day}T00:00:00Z`)

export function addDays(day: string, days: number) {
  const date = dateAtUtc(day)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function lastMonday(day: string) {
  return addDays(day, -((dateAtUtc(day).getUTCDay() + 6) % 7))
}

export const isMonday = (day: string) => dateAtUtc(day).getUTCDay() === 1
export const formatDay = (day: string) => dayFormatter.format(dateAtUtc(day))
export const formatTimestamp = (value: string) => timestampFormatter.format(new Date(value))
export const formatQuantity = (value: number | string) => numberFormatter.format(Number(value))
export const modelLabel = (model: string) => models[model] ?? model.replaceAll('_', ' ')
export const weekLabel = (value: number) => `${value} ${value === 1 ? 'week' : 'weeks'}`

export function integerInRange(value: string, min: number, max = Number.MAX_SAFE_INTEGER) {
  const number = Number(value)
  return /^\d+$/.test(value.trim()) && Number.isSafeInteger(number) && number >= min && number <= max
}

const forecastStatus: Record<string, string> = {
  unknown_coverage: 'Declare the dates with complete sales records and generate a new forecast.',
  coverage_ends_before_cutoff: 'Extend sales coverage through the Sunday before the review, or use an earlier Monday.',
  insufficient_history: 'This forecast needs more complete weeks of sales history for the requested horizon.',
  no_sales_signal: 'The covered sales history has no recorded demand for this product.',
}

export function forecastIssue(forecast: WeeklyForecast, protectionWeeks?: number) {
  const date = forecast.as_of_date
  if (!date || !isMonday(date)) return 'Choose a forecast run with a Monday review date.'
  const status = forecast.accuracy?.details?.status
  if (!forecast.accuracy) return 'This forecast run does not include the selected product.'
  if (status !== 'evaluated') {
    return (status && forecastStatus[status]) || 'An evaluated weekly forecast is required for this product.'
  }
  if (!forecast.predictions.length || (protectionWeeks && forecast.predictions.length < protectionWeeks)) {
    return 'The forecast is shorter than the saved policy’s protection period. Generate a new forecast.'
  }
  if (forecast.predictions.some((point, index) => point.period_start !== addDays(date, index * 7))) {
    return 'The weekly forecast must start on the review date and contain consecutive weeks.'
  }
  return ''
}
