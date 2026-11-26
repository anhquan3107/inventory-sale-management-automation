import { useState, type FormEvent } from 'react'
import { Alert, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type { WeeklyForecast } from '../../types/replenishment'
import { forecastIssue, formatDay, modelLabel, weekLabel } from './format'

interface Props {
  productId: number
  protectionWeeks?: number
  forecast: WeeklyForecast | null
  onForecast: (forecast: WeeklyForecast | null) => void
}

export default function SavedForecastForm({ productId, protectionWeeks, forecast, onForecast }: Props) {
  const [runId, setRunId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const issue = forecast && forecastIssue(forecast, protectionWeeks)

  async function load(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || !runId.trim()) return
    setBusy(true)
    setError('')
    onForecast(null)
    try {
      onForecast(await replenishmentApi.weeklyForecast(productId, runId.trim()))
    } catch (error) {
      setError(decisionError(error, 'Could not load the weekly forecast. Try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Paper
      component='section'
      elevation={0}
      aria-labelledby='saved-forecast-heading'
      sx={{ p: 3, borderRadius: 3 }}
    >
      <Typography id='saved-forecast-heading' variant='h6' component='h2' sx={{ mb: 2 }}>
        Saved weekly forecast
      </Typography>
      <Stack component='form' onSubmit={load} spacing={1.5}>
        <TextField
          label='Forecast run ID for this SKU'
          size='small'
          required
          value={runId}
          disabled={busy}
          onChange={(event) => {
            setRunId(event.target.value)
            setError('')
            onForecast(null)
          }}
        />
        <Button
          type='submit'
          variant='outlined'
          loading={busy}
          disabled={!runId.trim()}
          sx={{ alignSelf: 'flex-start' }}
        >
          Load forecast
        </Button>
        {error && <Alert severity='error'>{error}</Alert>}
        {issue && <Alert severity='warning'>{issue}</Alert>}
        {forecast?.as_of_date && (
          <Typography variant='body2' color='text.secondary'>Review date {formatDay(forecast.as_of_date)}</Typography>
        )}
        {forecast?.accuracy && !issue && (
          <Alert severity='success' role='status'>
            Evaluated weekly forecast · {modelLabel(forecast.accuracy.selected_model)} · {weekLabel(forecast.predictions.length)}
          </Alert>
        )}
      </Stack>
    </Paper>
  )
}
