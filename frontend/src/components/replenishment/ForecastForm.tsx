import { useState, type FormEvent } from 'react'
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material'
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
    <Paper component='section' elevation={0} aria-labelledby='forecast-heading' sx={{ p: 3, borderRadius: 3 }}>
      <Typography id='forecast-heading' variant='h6' component='h2' sx={{ mb: 2 }}>
        Weekly demand forecast
      </Typography>

      <Stack spacing={1.5}>
        <Paper elevation={0} sx={{ p: 2, borderRadius: 2, bgcolor: '#fafafa' }}>
          <Stack direction='row' alignItems='center' justifyContent='space-between' useFlexGap flexWrap='wrap' spacing={1}>
            <Box>
              <Typography variant='body2' color='text.secondary'>Sales coverage</Typography>
              <Typography variant='body1' sx={{ fontWeight: 600 }}>
                {coverage ? `${formatDay(coverage.observed_from)} – ${formatDay(coverage.observed_through)}` : 'No coverage declared'}
              </Typography>
            </Box>
            <Button size='small' variant='outlined' onClick={() => setCoverageOpen(true)} disabled={!!busy}>
              {coverage ? 'Edit coverage' : 'Set coverage'}
            </Button>
          </Stack>
        </Paper>

        <Stack component='form' onSubmit={generate} spacing={1.5}>
          <TextField
            label='Review date (UTC)'
            type='date'
            size='small'
            fullWidth
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
        </Stack>

        {coverage && monday && !covered && (
          <Alert severity='warning'>Use a Monday covered through the preceding Sunday, or update sales coverage.</Alert>
        )}

        <Box component='details' sx={{ pt: 1.5, borderTop: 1, borderColor: 'divider' }}>
          <Typography component='summary' variant='body2' sx={{ fontWeight: 600, cursor: 'pointer' }}>
            Use an existing forecast
          </Typography>
          <Stack component='form' spacing={1.5} sx={{ mt: 1.5 }}
            onSubmit={(event) => { event.preventDefault(); void run('load') }}>
            <TextField label='Forecast run ID' size='small' value={runId} disabled={!!busy}
              onChange={(event) => setRunId(event.target.value)} helperText='Leave blank to load the latest run.' />
            <Button type='submit' variant='outlined' disabled={!!busy} loading={busy === 'load'}>Load forecast</Button>
          </Stack>
        </Box>

        {error && <Alert severity='error'>{error}</Alert>}
        {issue && <Alert severity='warning'>{issue}</Alert>}
        {forecast && !issue && forecast.accuracy && (
          <Alert severity='success' role='status'>
            <Typography variant='body2' sx={{ fontWeight: 600 }}>Evaluated weekly forecast</Typography>
            <Typography variant='body2'>
              {weekLabel(forecast.predictions.length)} · {modelLabel(forecast.accuracy.selected_model)}
              {forecast.accuracy.mae != null && ` · MAE ${formatQuantity(forecast.accuracy.mae)} units`}
            </Typography>
          </Alert>
        )}
      </Stack>
      {coverageOpen && <CoverageDialog productId={productId} coverage={coverage}
        onSave={onCoverage} onClose={() => setCoverageOpen(false)} />}
    </Paper>
  )
}
