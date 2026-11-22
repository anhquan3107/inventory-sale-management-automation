import { useState, type FormEvent } from 'react'
import { Alert, Button, Paper, TextField } from '@mui/material'
import ShowChartOutlined from '@mui/icons-material/ShowChartOutlined'
import CalendarMonthOutlined from '@mui/icons-material/CalendarMonthOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline'
import type { SalesCoverage, WeeklyForecast } from '../../types/replenishment'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import { addDays, forecastIssue, formatDay, formatQuantity, isMonday, lastMonday, modelLabel, todayUtc, weekLabel } from './format'
import CoverageDialog from './CoverageDialog'

interface Props {
  productId: number
  protectionWeeks?: number
  policyDirty: boolean
  coverage?: SalesCoverage
  forecast: WeeklyForecast | null
  onCoverage: (coverage: SalesCoverage) => void
  onForecast: (forecast: WeeklyForecast | null) => void
}

export default function ForecastForm({ productId, protectionWeeks, policyDirty, coverage, forecast, onCoverage, onForecast }: Props) {
  const today = todayUtc()
  const [date, setDate] = useState(() => {
    const latestCovered = coverage ? addDays(coverage.observed_through, 1) : today
    return lastMonday(latestCovered < today ? latestCovered : today)
  })
  const [runId, setRunId] = useState('')
  const [busy, setBusy] = useState<'generate' | 'load' | null>(null)
  const [error, setError] = useState('')
  const [coverageOpen, setCoverageOpen] = useState(false)
  const monday = isMonday(date) && date <= today
  const covered = !!(coverage && monday && coverage.observed_from < date
    && coverage.observed_through >= addDays(date, -1))
  const issue = forecast && forecastIssue(forecast, protectionWeeks)

  async function run(action: 'generate' | 'load') {
    if (busy || (action === 'generate' && (!protectionWeeks || policyDirty || !covered))) return
    setBusy(action)
    setError('')
    onForecast(null)
    let createdRunId: string | undefined
    try {
      if (action === 'generate' && protectionWeeks) {
        createdRunId = await replenishmentApi.generateForecast(productId, date, protectionWeeks)
        setRunId(createdRunId)
      }
      const result = await replenishmentApi.weeklyForecast(productId, createdRunId ?? (runId.trim() || undefined))
      onForecast(result)
      if (result.as_of_date && isMonday(result.as_of_date)) setDate(result.as_of_date)
    } catch (error) {
      const message = decisionError(error, 'Could not load the weekly forecast. Try again.')
      setError(createdRunId ? `Forecast saved. Use its run ID to reload the evidence. ${message}` : message)
    } finally {
      setBusy(null)
    }
  }

  function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void run('generate')
  }

  return (
    <Paper component='section' variant='outlined' className='rp-card' aria-labelledby='forecast-heading'>
      <div className='rp-card-heading'>
        <span className='rp-section-icon'><ShowChartOutlined fontSize='small' /></span>
        <div>
          <h2 id='forecast-heading'>Weekly demand forecast</h2>
          <p>Use evaluated demand to cover the saved protection period.</p>
        </div>
      </div>
      <div className='rp-form'>
        <div className='rp-coverage'>
          <CalendarMonthOutlined fontSize='small' aria-hidden='true' />
          <div>
            <strong>Sales coverage</strong>
            <span>{coverage ? `${formatDay(coverage.observed_from)} – ${formatDay(coverage.observed_through)}` : 'Complete sales dates are required to generate a forecast.'}</span>
          </div>
          <Button size='small' onClick={() => setCoverageOpen(true)} disabled={!!busy}>
            {coverage ? 'Edit coverage' : 'Set coverage'}
          </Button>
        </div>
        <form className='rp-forecast-controls' onSubmit={generate}>
          <TextField
            label='Review date (UTC)'
            type='date'
            size='small'
            required
            value={date}
            onChange={(event) => {
              setDate(event.target.value)
              setError('')
              onForecast(null)
            }}
            disabled={!!busy}
            error={!!date && !monday}
            helperText={monday ? 'Monday review' : 'Choose a Monday on or before today'}
            slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: today } }}
          />
          <Button type='submit' variant='outlined' loading={busy === 'generate'}
            disabled={!!busy || !protectionWeeks || policyDirty || !covered}>
            Generate forecast
          </Button>
        </form>
        {coverage && monday && !covered && (
          <Alert severity='warning'>Use a Monday covered through the preceding Sunday, or update sales coverage.</Alert>
        )}
        <details className='rp-existing-run'>
          <summary>Use an existing forecast</summary>
          <form className='rp-forecast-controls' onSubmit={(event) => { event.preventDefault(); void run('load') }}>
            <TextField label='Forecast run ID' size='small' value={runId} disabled={!!busy}
              onChange={(event) => setRunId(event.target.value)} helperText='Leave blank to load the latest run.' />
            <Button type='submit' variant='outlined' disabled={!!busy} loading={busy === 'load'}>Load forecast</Button>
          </form>
        </details>
        {error && <Alert severity='error'>{error}</Alert>}
        {issue && <Alert severity='warning'>{issue}</Alert>}
        {forecast && !issue && forecast.accuracy && (
          <div className='rp-forecast-ready' role='status'>
            <CheckCircleOutline fontSize='small' aria-hidden='true' />
            <div>
              <strong>Evaluated weekly forecast</strong>
              <span>{weekLabel(forecast.predictions.length)} · {modelLabel(forecast.accuracy.selected_model)}
                {forecast.accuracy.mae != null && ` · MAE ${formatQuantity(forecast.accuracy.mae)} units`}
              </span>
            </div>
          </div>
        )}
      </div>
      {coverageOpen && <CoverageDialog productId={productId} coverage={coverage}
        onSave={onCoverage} onClose={() => setCoverageOpen(false)} />}
    </Paper>
  )
}
