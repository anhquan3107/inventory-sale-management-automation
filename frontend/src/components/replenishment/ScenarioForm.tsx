import { useRef, useState, type FormEvent } from 'react'
import { Alert, Button, Checkbox, FormControlLabel, IconButton, Paper, Radio, RadioGroup, TextField } from '@mui/material'
import AddOutlined from '@mui/icons-material/AddOutlined'
import CalculateOutlined from '@mui/icons-material/CalculateOutlined'
import Inventory2Outlined from '@mui/icons-material/Inventory2Outlined'
import ScienceOutlined from '@mui/icons-material/ScienceOutlined'
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
    <Paper component='section' variant='outlined' className='rp-card' aria-labelledby='scenario-heading'>
      <div className='rp-card-heading'>
        <span className='rp-section-icon'><CalculateOutlined fontSize='small' /></span>
        <div>
          <h2 id='scenario-heading'>Order recommendation</h2>
          <p>Choose the inventory inputs for the calculation.</p>
        </div>
      </div>
      <form onSubmit={generate} className='rp-form'>
        <RadioGroup className='rp-mode-group' aria-label='Inventory mode' name='replenishment-mode' value={mode}
          onChange={(_, value) => { setMode(value as RecommendationMode); setConfirmed(false); setError('') }}>
          {([
            ['simulation', 'Simulation', 'Enter stock and receipts', <ScienceOutlined fontSize='small' />],
            ['live', 'Live inventory', 'Use recorded on-hand stock', <Inventory2Outlined fontSize='small' />],
          ] as const).map(([value, label, description, icon]) => (
            <FormControlLabel className='rp-mode' key={value} data-selected={mode === value}
              value={value} control={<Radio size='small' />} disabled={busy}
              label={<>{icon}<span><strong>{label}</strong><small>{description}</small></span></>} />
          ))}
        </RadioGroup>
        {mode === 'simulation' ? (
          <>
            <TextField label='Simulated on-hand stock' size='small' required value={onHand}
              disabled={busy} onChange={(event) => { setOnHand(event.target.value); setError('') }}
              slotProps={{ htmlInput: { inputMode: 'numeric' } }} />
            <div className='rp-receipts'>
              <div className='rp-receipts-heading'>
                <strong>Expected receipts <span>(optional)</span></strong>
                <Button startIcon={<AddOutlined />} size='small' onClick={addReceipt} disabled={busy || receipts.length >= 100}>
                  Add receipt
                </Button>
              </div>
              {receipts.length > 0 && <p className='rp-small rp-no-margin'>Receipts arrive at the start of the selected week. Week 1 starts on the review date.</p>}
              {receipts.map(({ id, arrivalWeek, quantity }, index) => (
                <div className='rp-receipt-row' key={id}>
                  <TextField label={`Receipt ${index + 1} arrival week`} size='small' required value={arrivalWeek}
                    disabled={busy} onChange={(event) => changeReceipt(id, 'arrivalWeek', event.target.value)}
                    slotProps={{ htmlInput: { inputMode: 'numeric' } }} />
                  <TextField label={`Receipt ${index + 1} units`} size='small' required value={quantity}
                    disabled={busy} onChange={(event) => changeReceipt(id, 'quantity', event.target.value)}
                    slotProps={{ htmlInput: { inputMode: 'numeric' } }} />
                  <IconButton aria-label={`Remove receipt ${index + 1}`} disabled={busy}
                    onClick={() => { setReceipts((items) => items.filter((item) => item.id !== id)); setError('') }}>
                    <DeleteOutline />
                  </IconButton>
                </div>
              ))}
            </div>
          </>
        ) : (
          <FormControlLabel
            control={<Checkbox checked={confirmed} disabled={busy || !liveAvailable}
              onChange={(event) => { setConfirmed(event.target.checked); setError('') }} />}
            label='I confirm there are no incoming supplier orders for this product.'
          />
        )}
        {error && <Alert severity='error'>{error}</Alert>}
        <div className='rp-actions'>
          <Button type='submit' variant='contained' loading={busy}
            disabled={!!blocker || (mode === 'live' && !confirmed)} startIcon={<CalculateOutlined />}>
            Generate recommendation
          </Button>
          {blocker && <span className='rp-small'>{blocker}</span>}
        </div>
      </form>
    </Paper>
  )
}
