import { useState, type FormEvent } from 'react'
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem,
  Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from '@mui/material'
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
  const { policy, result, diagnostics } = snapshot
  const receipts = snapshot.request?.simulated_receipts ?? []
  const receiptTotal = receipts.reduce((total, item) => total + item.quantity, 0)
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

  const history = decision && (
    <Stack spacing={1} role='status'>
      <Stack direction='row' alignItems='center' useFlexGap flexWrap='wrap' spacing={1}>
        <Chip label={status} size='small' sx={{ textTransform: 'capitalize' }} />
        <Typography variant='body2'>{formatQuantity(decision.quantity)} units · {formatTimestamp(decision.created_at)}</Typography>
      </Stack>
      <Typography variant='body2' color='text.secondary'>Recorded by user #{decision.user_id}</Typography>
      {decision.reason && <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{decision.reason}</Typography>}
    </Stack>
  )

  if (!policy || !result || !snapshot.request || !Array.isArray(snapshot.forecast)
    || !Array.isArray(result.projected_week_end_stock) || !snapshot.decision_date) {
    return (
      <Dialog open onClose={onClose} fullWidth maxWidth='sm' aria-labelledby='recommendation-title'>
        <DialogTitle id='recommendation-title'>Recommendation #{recommendation.id}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Alert severity='warning'>This historical snapshot has incomplete evidence.</Alert>
            {history}
          </Stack>
        </DialogContent>
        <DialogActions><Button onClick={onClose}>Close</Button></DialogActions>
      </Dialog>
    )
  }

  const policyFacts = [
    ['Lead time', weekLabel(policy.lead_time_weeks)],
    ['Review interval', weekLabel(policy.review_interval_weeks)],
    ['Lead-time demand', `${formatQuantity(result.lead_time_demand)} units`],
    ['Safety stock', `${formatQuantity(policy.safety_stock)} units`],
    ['Minimum order / pack size', `${formatQuantity(policy.minimum_order_quantity)} / ${formatQuantity(policy.pack_size)} units`],
    ['Demand model', snapshot.model ? modelLabel(snapshot.model) : 'Unavailable'],
    ['Dataset', snapshot.dataset_version ?? 'Unavailable'],
    ['Forecast run', snapshot.request.run_id],
  ]

  return (
    <Dialog open onClose={busy ? undefined : onClose} fullWidth maxWidth='md' aria-labelledby='recommendation-title'>
      <DialogTitle id='recommendation-title'>Recommendation #{recommendation.id}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Box>
            <Typography variant='h6' component='h2' sx={{ overflowWrap: 'anywhere' }}>{productLabel}</Typography>
            <Typography variant='body2' color='text.secondary'>
              {snapshot.mode === 'live' ? 'Live inventory' : 'Simulation'} · {formatDay(snapshot.decision_date)} · Policy v{policy.version}
            </Typography>
          </Box>

          <Paper elevation={0} sx={{ p: 2, borderRadius: 2, bgcolor: '#fafafa' }}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Typography variant='body2' color='text.secondary'>Suggested order</Typography>
                <Typography variant='h6'>{formatQuantity(recommendation.suggested_quantity)} units</Typography>
                <Typography variant='body2' color='text.secondary'>
                  {recommendation.action === 'reorder' ? 'Reorder' : 'No order needed'}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Typography variant='body2' color='text.secondary'>Target stock</Typography>
                <Typography variant='h6'>{formatQuantity(result.target_stock)} units</Typography>
                <Typography variant='body2' color='text.secondary'>
                  {formatQuantity(result.protection_demand)} forecast + {formatQuantity(policy.safety_stock)} safety
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Typography variant='body2' color='text.secondary'>Inventory position</Typography>
                <Typography variant='h6'>{formatQuantity(result.inventory_position)} units</Typography>
                <Typography variant='body2' color='text.secondary'>
                  {formatQuantity(snapshot.on_hand)} on hand + {formatQuantity(receiptTotal)} incoming
                </Typography>
              </Grid>
            </Grid>
          </Paper>

          <Box component='section' aria-labelledby='projection-heading'>
            <Stack direction='row' alignItems='flex-start' justifyContent='space-between' useFlexGap flexWrap='wrap' spacing={1} sx={{ mb: 1.5 }}>
              <Box>
                <Typography id='projection-heading' variant='h6' component='h3'>Projected week-end stock</Typography>
                <Typography variant='body2' color='text.secondary'>
                  Receipts are added at the start of each week, then forecast demand is subtracted. The suggested order is excluded.
                </Typography>
              </Box>
            </Stack>
            {diagnostics?.status === 'available' ? (
              diagnostics.first_shortage_period_start && diagnostics.first_shortage_quantity !== null ? (
                <Alert severity={diagnostics.shortage_during_lead_time ? 'error' : 'warning'} sx={{ mb: 1.5 }}>
                  Shortage projected in the week beginning {formatDay(diagnostics.first_shortage_period_start)}
                  {' '}({formatQuantity(diagnostics.first_shortage_quantity)} units short).
                  {' '}Maximum projected deficit {formatQuantity(diagnostics.maximum_projected_deficit)} units.
                  {' '}{diagnostics.shortage_during_lead_time ? 'The shortage falls within lead time.' : 'The shortage falls after lead time.'}
                </Alert>
              ) : (
                <Alert severity='info' sx={{ mb: 1.5 }}>No shortage projected during the protection period.</Alert>
              )
            ) : (
              <Alert severity='warning' sx={{ mb: 1.5 }}>Shortage diagnostics are unavailable for this snapshot.</Alert>
            )}
            <TableContainer>
              <Table size='small'>
                <TableHead>
                  <TableRow>
                    <TableCell scope='col'>Week of</TableCell>
                    <TableCell scope='col' align='right'>Demand</TableCell>
                    <TableCell scope='col' align='right'>Receipts</TableCell>
                    <TableCell scope='col' align='right'>Ending stock</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.projected_week_end_stock.map((value, index) => {
                    const week = snapshot.forecast[index]
                    if (!week) return null
                    const incoming = receipts.reduce((total, item) => item.arrival_week === index + 1 ? total + item.quantity : total, 0)
                    return (
                      <TableRow key={week.period_start} hover>
                        <TableCell component='th' scope='row' sx={{ whiteSpace: 'nowrap' }}>{formatDay(week.period_start)}</TableCell>
                        <TableCell align='right'>{formatQuantity(week.quantity)}</TableCell>
                        <TableCell align='right'>{formatQuantity(incoming)}</TableCell>
                        <TableCell align='right' sx={{ fontWeight: Number(value) < 0 ? 700 : undefined }}>{formatQuantity(value)}</TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          {diagnostics?.status === 'available' && diagnostics.excess_stock_review
            && diagnostics.excess_stock_threshold !== null && diagnostics.excess_above_review_threshold !== null && (
            <Alert severity='warning'>
              Excess-stock review. Inventory position, including incoming receipts, is
              {' '}{formatQuantity(diagnostics.excess_above_review_threshold)} units over the threshold of
              {' '}{formatQuantity(diagnostics.excess_stock_threshold)} units ({diagnostics.excess_stock_factor} times target stock).
            </Alert>
          )}
          {diagnostics?.status === 'available' && diagnostics.zero_demand_stock_review && (
            <Alert severity='warning'>Review the positive inventory position against a target stock of zero.</Alert>
          )}

          <Box component='details'>
            <Typography component='summary' variant='body2' sx={{ fontWeight: 600, cursor: 'pointer' }}>
              Policy and forecast used
            </Typography>
            <TableContainer sx={{ mt: 1 }}>
              <Table size='small' aria-label='Policy and forecast used'>
                <TableBody>
                  {policyFacts.map(([label, value]) => (
                    <TableRow key={label}>
                      <TableCell component='th' scope='row' sx={{ fontWeight: 600 }}>{label}</TableCell>
                      <TableCell sx={{ overflowWrap: 'anywhere' }}>{value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          <Box component='section' aria-labelledby='review-heading' sx={{ pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography id='review-heading' variant='h6' component='h3' sx={{ mb: 1 }}>Review decision</Typography>
            {status === 'pending' ? (
              <Stack id='recommendation-review-form' component='form' spacing={1.5} onSubmit={review}>
                <Typography variant='body2' color='text.secondary'>
                  This records an advisory decision. Purchase orders and inventory updates are handled separately.
                </Typography>
                <Grid container spacing={1.5}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField select label='Decision' size='small' fullWidth value={action} disabled={busy}
                      onChange={(event) => { setAction(event.target.value as DecisionAction); setError('') }}>
                      <MenuItem value='approved'>Approve suggested order</MenuItem>
                      <MenuItem value='modified'>Modify quantity</MenuItem>
                      <MenuItem value='rejected'>Reject recommendation</MenuItem>
                    </TextField>
                  </Grid>
                  {action === 'modified' && (
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField label='Revised quantity' size='small' fullWidth required value={quantity} disabled={busy}
                        onChange={(event) => { setQuantity(event.target.value); setError('') }}
                        slotProps={{ htmlInput: { inputMode: 'numeric' } }}
                        helperText={`Minimum ${formatQuantity(policy.minimum_order_quantity)} · Pack size ${formatQuantity(policy.pack_size)}`} />
                    </Grid>
                  )}
                </Grid>
                <TextField label={action === 'modified' ? 'Reason' : 'Reason (optional)'} multiline minRows={2}
                  value={reason} disabled={busy} required={action === 'modified'}
                  onChange={(event) => { setReason(event.target.value); setError('') }}
                  slotProps={{ htmlInput: { maxLength: 2000 } }} />
              </Stack>
            ) : history}
            {error && <Alert severity='error' sx={{ mt: 2 }}>{error}</Alert>}
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Close</Button>
        {status === 'pending' && (
          <Button type='submit' form='recommendation-review-form' variant='contained' loading={busy}>Record decision</Button>
        )}
      </DialogActions>
    </Dialog>
  )
}
