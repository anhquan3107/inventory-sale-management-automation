import { useState, type FormEvent } from 'react'
import {
  Alert, Button, Dialog, DialogContent, IconButton, MenuItem, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
} from '@mui/material'
import CloseOutlined from '@mui/icons-material/CloseOutlined'
import { isAxiosError } from 'axios'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type { DecisionAction, Recommendation } from '../../types/replenishment'
import { formatDay, formatQuantity, formatTimestamp, integerInRange, modelLabel, weekLabel } from './format'

interface Props {
  recommendation: Recommendation
  productLabel: string
  onUpdate: (recommendation: Recommendation) => void
  onClose: () => void
}

export default function RecommendationDetail({ recommendation, productLabel, onUpdate, onClose }: Props) {
  const { snapshot, decision, status } = recommendation
  const { policy, result } = snapshot
  const receipts = snapshot.request.simulated_receipts ?? []
  const receiptTotal = receipts.reduce((total, item) => total + item.quantity, 0)
  const maxStock = Math.max(1, ...result.projected_week_end_stock.map((value) => Math.abs(Number(value))))
  const [action, setAction] = useState<DecisionAction>('approved')
  const [quantity, setQuantity] = useState(String(recommendation.suggested_quantity))
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || status !== 'pending') return
    const revisedQuantity = Number(quantity)
    if (action === 'modified') {
      if (!integerInRange(quantity, 0) || !reason.trim()) {
        setError('Enter a whole quantity and a reason for the modification.')
        return
      }
      const meetsOrderConstraints = revisedQuantity >= policy.minimum_order_quantity
        && revisedQuantity % policy.pack_size === 0
      if (revisedQuantity > 0 && !meetsOrderConstraints) {
        setError('The order must meet the minimum and be a multiple of the pack size.')
        return
      }
    }
    setBusy(true)
    setError('')
    try {
      onUpdate(await replenishmentApi.review(recommendation.id, {
        action,
        ...(action === 'modified' && { quantity: revisedQuantity }),
        ...(reason.trim() && { reason: reason.trim() }),
      }))
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 409) {
        const current = await replenishmentApi.recommendation(recommendation.id).catch(() => null)
        if (current && current.status !== 'pending') onUpdate(current)
      }
      setError(decisionError(error, 'Could not record the decision. Try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open onClose={busy ? undefined : onClose} fullWidth maxWidth='md'
      aria-labelledby='recommendation-title' slotProps={{ paper: { className: 'rp-detail' } }}>
      <header className='rp-detail-header'>
        <div>
          <p className='rp-detail-reference'>Recommendation #{recommendation.id}</p>
          <h2 id='recommendation-title'>{productLabel}</h2>
          <p className='rp-muted rp-no-margin'>
            {snapshot.mode === 'live' ? 'Live inventory' : 'Simulation'} · {formatDay(snapshot.decision_date)} · Policy v{policy.version}
          </p>
        </div>
        <IconButton aria-label='Close recommendation' onClick={onClose} disabled={busy}><CloseOutlined /></IconButton>
      </header>
      <DialogContent dividers>
        <div className='rp-detail-content'>
          <div className='rp-metrics'>
            <div className='rp-metric rp-metric-primary'>
              <span>Suggested order</span>
              <strong>{formatQuantity(recommendation.suggested_quantity)} <small>units</small></strong>
              <span>{recommendation.action === 'reorder' ? 'Reorder' : 'No order needed'}</span>
            </div>
            <div className='rp-metric'>
              <span>Target stock</span>
              <strong>{formatQuantity(result.target_stock)} <small>units</small></strong>
              <span>{formatQuantity(result.protection_demand)} forecast + {formatQuantity(policy.safety_stock)} safety</span>
            </div>
            <div className='rp-metric'>
              <span>Inventory position</span>
              <strong>{formatQuantity(result.inventory_position)} <small>units</small></strong>
              <span>{formatQuantity(snapshot.on_hand)} on hand + {formatQuantity(receiptTotal)} incoming</span>
            </div>
          </div>
          <section aria-labelledby='projection-heading'>
            <div className='rp-projection-heading'>
              <div>
                <h3 id='projection-heading'>Projected week-end stock</h3>
                <p className='rp-muted rp-no-margin'>Based on on-hand stock, forecast demand and existing receipts.</p>
              </div>
              <span className={`rp-badge ${result.stockout_risk ? 'rp-amber' : 'rp-green'}`}>
                {result.stockout_risk ? 'Stockout risk' : 'No projected stockout'}
              </span>
            </div>
            <TableContainer className='rp-table-wrap'>
              <Table className='rp-table rp-projection'>
                <TableHead><TableRow><TableCell scope='col'>Week of</TableCell><TableCell scope='col'>Demand</TableCell><TableCell scope='col'>Receipts</TableCell><TableCell scope='col'>Ending stock</TableCell></TableRow></TableHead>
                <TableBody>
                  {result.projected_week_end_stock.map((value, index) => {
                    const week = snapshot.forecast[index]
                    const incoming = receipts.reduce((total, item) => item.arrival_week === index + 1 ? total + item.quantity : total, 0)
                    const negative = Number(value) < 0
                    return (
                      <TableRow key={week.period_start}>
                        <TableCell component='th' scope='row'>{formatDay(week.period_start)}</TableCell>
                        <TableCell>{formatQuantity(week.quantity)}</TableCell>
                        <TableCell>{formatQuantity(incoming)}</TableCell>
                        <TableCell>
                          <span className={`rp-stock-cell${negative ? ' rp-stock-negative' : ''}`}>
                            <span className='rp-stock-track' aria-hidden='true'>
                              <span style={{ width: `${Math.abs(Number(value)) / maxStock * 100}%` }} />
                            </span>
                            <strong>{formatQuantity(value)}</strong>
                          </span>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </section>
          <details className='rp-existing-run'>
            <summary>Policy and forecast used</summary>
            <dl className='rp-snapshot'>
              <div><dt>Lead time</dt><dd>{weekLabel(policy.lead_time_weeks)}</dd></div>
              <div><dt>Review interval</dt><dd>{weekLabel(policy.review_interval_weeks)}</dd></div>
              <div><dt>Lead-time demand</dt><dd>{formatQuantity(result.lead_time_demand)} units</dd></div>
              <div><dt>Safety stock</dt><dd>{formatQuantity(policy.safety_stock)} units</dd></div>
              <div><dt>Minimum / pack</dt><dd>{formatQuantity(policy.minimum_order_quantity)} / {formatQuantity(policy.pack_size)} units</dd></div>
              <div><dt>Demand model</dt><dd>{modelLabel(snapshot.model)}</dd></div>
              <div><dt>Dataset</dt><dd>{snapshot.dataset_version ?? 'Unavailable'}</dd></div>
              <div><dt>Forecast run</dt><dd>{snapshot.request.run_id}</dd></div>
            </dl>
          </details>
          <section aria-labelledby='review-heading' className='rp-review'>
            <h3 id='review-heading'>Review decision</h3>
            {status === 'pending' ? (
              <form className='rp-form' onSubmit={review}>
                <p className='rp-muted rp-no-margin'>This records an advisory decision. Purchase orders and inventory updates are handled separately.</p>
                <div className='rp-fields'>
                  <TextField select label='Decision' size='small' value={action} disabled={busy}
                    onChange={(event) => { setAction(event.target.value as DecisionAction); setError('') }}>
                    <MenuItem value='approved'>Approve suggested order</MenuItem>
                    <MenuItem value='modified'>Modify quantity</MenuItem>
                    <MenuItem value='rejected'>Reject recommendation</MenuItem>
                  </TextField>
                  {action === 'modified' && (
                    <TextField label='Revised quantity' size='small' required value={quantity} disabled={busy}
                      onChange={(event) => { setQuantity(event.target.value); setError('') }}
                      slotProps={{ htmlInput: { inputMode: 'numeric' } }}
                      helperText={`Minimum ${formatQuantity(policy.minimum_order_quantity)} · Pack size ${formatQuantity(policy.pack_size)}`} />
                  )}
                </div>
                <TextField label={action === 'modified' ? 'Reason' : 'Reason (optional)'} multiline minRows={2}
                  value={reason} disabled={busy} required={action === 'modified'}
                  onChange={(event) => { setReason(event.target.value); setError('') }}
                  slotProps={{ htmlInput: { maxLength: 2000 } }} />
                <div className='rp-actions'>
                  <Button type='submit' variant='contained' loading={busy}>Record decision</Button>
                </div>
              </form>
            ) : decision && (
              <div className='rp-form' role='status'>
                <p className='rp-no-margin'>
                  <span className={`rp-badge rp-${status}`}>{status}</span>
                  {' '}{formatQuantity(decision.quantity)} units · {formatTimestamp(decision.created_at)}
                </p>
                <p className='rp-muted rp-no-margin'>Recorded by user #{decision.user_id}</p>
                {decision.reason && <p className='rp-decision-reason rp-no-margin'>{decision.reason}</p>}
              </div>
            )}
            {error && <Alert severity='error' sx={{ mt: 2 }}>{error}</Alert>}
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}
