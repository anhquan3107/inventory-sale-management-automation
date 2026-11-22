import { useRef, useState, type FormEvent } from 'react'
import { Alert, Button, Checkbox, FormControlLabel, Grid, IconButton, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material'
import DeleteOutline from '@mui/icons-material/DeleteOutline'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type {
  Recommendation, RecommendationMode, RecommendationRequest, ReplenishmentPolicy, WeeklyForecast,
} from '../../types/replenishment'
import { forecastIssue, integerInRange, isMonday, todayUtc } from './format'

interface ReceiptDraft {
  id: number
  arrivalWeek: string
  quantity: string
}

interface Props {
  productId: number
  policy?: ReplenishmentPolicy
  policyDirty: boolean
  forecast: WeeklyForecast | null
  onGenerate: (result: Recommendation) => void
}

export default function ScenarioForm({ productId, policy, policyDirty, forecast, onGenerate }: Props) {
  const [mode, setMode] = useState<RecommendationMode>('simulation')
  const [onHand, setOnHand] = useState('')
  const [receipts, setReceipts] = useState<ReceiptDraft[]>([])
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const receiptId = useRef(0)
  const retry = useRef<{ signature: string; key: string } | null>(null)
  const today = todayUtc()
  const protectionWeeks = policy ? policy.lead_time_weeks + policy.review_interval_weeks : undefined
  const liveAvailable = forecast?.as_of_date === today && isMonday(today)
  const ready = !!forecast && !forecastIssue(forecast, protectionWeeks)
  const blocker = !policy ? 'Save a replenishment policy first.'
    : policyDirty ? 'Save or reset the policy edits to continue.'
    : !ready ? 'Load an evaluated weekly forecast to continue.'
    : mode === 'live' && !liveAvailable ? 'Live mode uses a forecast for today’s Monday review (UTC).'
    : ''

  function changeReceipt(id: number, field: 'arrivalWeek' | 'quantity', value: string) {
    setReceipts((items) => items.map((item) => item.id === id ? { ...item, [field]: value } : item))
    setError('')
  }

  function addReceipt() {
    const id = receiptId.current++
    setReceipts((items) => [...items, { id, arrivalWeek: '1', quantity: '' }])
    setError('')
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (blocker || busy || !forecast || (mode === 'live' && !confirmed)) return
    if (mode === 'simulation' && (!integerInRange(onHand, 0) || receipts.some(
      ({ arrivalWeek, quantity }) => !integerInRange(arrivalWeek, 1, 26) || !integerInRange(quantity, 1),
    ))) {
      setError('Enter whole units for stock and receipts, with arrival weeks from 1 to 26.')
      return
    }

    const input: Omit<RecommendationRequest, 'request_key'> = {
      run_id: forecast.run_id,
      product_id: productId,
      mode,
      ...(mode === 'live' ? { confirms_no_incoming_orders: true } : {
        simulated_on_hand: Number(onHand),
        simulated_receipts: receipts.map(({ arrivalWeek, quantity }) => ({
          arrival_week: Number(arrivalWeek),
          quantity: Number(quantity),
        })),
      }),
    }
    const signature = JSON.stringify([input, policy?.version])
    const key = retry.current?.signature === signature ? retry.current.key : crypto.randomUUID()
    retry.current = { signature, key }
    setBusy(true)
    setError('')
    try {
      const result = await replenishmentApi.generateRecommendation({ ...input, request_key: key })
      retry.current = null
      onGenerate(result)
    } catch (error) {
      setError(decisionError(error, 'Could not generate the recommendation. Retry to recover the same request.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Paper component='section' elevation={0} aria-labelledby='scenario-heading' sx={{ p: 3, borderRadius: 3 }}>
      <Typography id='scenario-heading' variant='h6' component='h2' sx={{ mb: 2 }}>
        Order recommendation
      </Typography>

      <Stack component='form' onSubmit={generate} spacing={1.5}>
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
            <TextField
              select
              label='Inventory mode'
              size='small'
              fullWidth
              value={mode}
              disabled={busy}
              onChange={(event) => {
                setMode(event.target.value as RecommendationMode)
                setConfirmed(false)
                setError('')
              }}
            >
              <MenuItem value='simulation'>Simulation</MenuItem>
              <MenuItem value='live'>Live inventory</MenuItem>
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, lg: 8 }}>
            {mode === 'simulation' ? (
              <TextField label='Simulated on-hand stock' size='small' fullWidth required value={onHand}
                disabled={busy} onChange={(event) => { setOnHand(event.target.value); setError('') }}
                slotProps={{ htmlInput: { inputMode: 'numeric' } }} />
            ) : (
              <FormControlLabel
                control={<Checkbox checked={confirmed} disabled={busy || !liveAvailable}
                  onChange={(event) => { setConfirmed(event.target.checked); setError('') }} />}
                label='I confirm there are no incoming supplier orders for this product.'
              />
            )}
          </Grid>
        </Grid>

        {mode === 'simulation' && (
          <Stack spacing={1.5}>
            <Stack direction='row' alignItems='center' justifyContent='space-between' useFlexGap flexWrap='wrap' spacing={1}>
              <Typography variant='body2' sx={{ fontWeight: 600 }}>Expected receipts (optional)</Typography>
              <Button size='small' variant='outlined' onClick={addReceipt} disabled={busy || receipts.length >= 100}>
                Add receipt
              </Button>
            </Stack>
            {receipts.length > 0 && (
              <Typography variant='body2' color='text.secondary'>
                Receipts arrive at the start of the selected week. Week 1 starts on the review date.
              </Typography>
            )}
            {receipts.map(({ id, arrivalWeek, quantity }, index) => (
              <Stack key={id} direction='row' spacing={1.5} alignItems='center'>
                <TextField label={`Receipt ${index + 1} arrival week`} size='small' fullWidth required value={arrivalWeek}
                  disabled={busy} onChange={(event) => changeReceipt(id, 'arrivalWeek', event.target.value)}
                  slotProps={{ htmlInput: { inputMode: 'numeric' } }} />
                <TextField label={`Receipt ${index + 1} units`} size='small' fullWidth required value={quantity}
                  disabled={busy} onChange={(event) => changeReceipt(id, 'quantity', event.target.value)}
                  slotProps={{ htmlInput: { inputMode: 'numeric' } }} />
                <IconButton aria-label={`Remove receipt ${index + 1}`} disabled={busy}
                  onClick={() => { setReceipts((items) => items.filter((item) => item.id !== id)); setError('') }}>
                  <DeleteOutline />
                </IconButton>
              </Stack>
            ))}
          </Stack>
        )}

        {error && <Alert severity='error'>{error}</Alert>}
        <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} justifyContent='flex-end' spacing={1.5}>
          {blocker && <Typography variant='body2' color='text.secondary'>{blocker}</Typography>}
          <Button type='submit' variant='contained' loading={busy}
            disabled={!!blocker || (mode === 'live' && !confirmed)}>
            Generate recommendation
          </Button>
        </Stack>
      </Stack>
    </Paper>
  )
}
