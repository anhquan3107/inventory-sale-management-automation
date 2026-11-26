import { useEffect, useState, type FormEvent } from 'react'
import {
  Alert, Box, Button, Chip, CircularProgress, Grid, MenuItem, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TablePagination, TableRow, TextField, Typography,
} from '@mui/material'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type {
  ExceptionClassification, ExceptionQuery, ExceptionScope, InventoryExceptionPage,
  Recommendation, RecommendationMode, ReviewStatus,
} from '../../types/replenishment'
import { formatDay, formatQuantity } from './format'

const classificationLabels: Record<ExceptionClassification, string> = {
  shortage_within_lead_time: 'Shortage within lead time',
  shortage_after_lead_time: 'Shortage after lead time',
  planned_replenishment: 'Planned replenishment',
  excess_stock_review: 'Excess-stock review',
  insufficient_evidence: 'Insufficient evidence',
  not_generated: 'Recommendation not generated',
  unsupported_snapshot: 'Unsupported snapshot',
  no_exception: 'No exception',
}

const reviewLabels: Record<ReviewStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  modified: 'Modified',
  rejected: 'Rejected',
}

const defaultScope: ExceptionScope = { run_id: '', mode: 'simulation' }
const pageSize = 10

interface Props {
  initialScope?: ExceptionScope
  refreshKey: string
  onOpen: (recommendation: Recommendation) => void
}

interface Result {
  query: ExceptionQuery
  refreshKey: string
  page?: InventoryExceptionPage
  error?: string
}

export default function ExceptionWorkspace({ initialScope, refreshKey, onOpen }: Props) {
  const [scope, setScope] = useState(initialScope ?? defaultScope)
  const [classification, setClassification] = useState<ExceptionClassification | ''>('')
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | ''>('')
  const [query, setQuery] = useState<ExceptionQuery | null>(
    initialScope ? { ...initialScope, limit: pageSize, offset: 0 } : null,
  )
  const [result, setResult] = useState<Result | null>(null)
  const [openingId, setOpeningId] = useState<number | null>(null)
  const [detailError, setDetailError] = useState('')
  const ready = result?.query === query && result.refreshKey === refreshKey
  const page = ready ? result.page : undefined

  useEffect(() => {
    if (!query) return
    const controller = new AbortController()
    replenishmentApi.exceptions(query, controller.signal)
      .then((page) => { if (!controller.signal.aborted) setResult({ query, refreshKey, page }) })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({
          query, refreshKey, error: decisionError(error, 'Could not load inventory exceptions. Try again.'),
        })
      })
    return () => controller.abort()
  }, [query, refreshKey])

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!scope.run_id.trim()) return
    setDetailError('')
    setQuery({ ...scope, run_id: scope.run_id.trim(), classification: classification || undefined,
      review_status: reviewStatus || undefined, limit: pageSize, offset: 0 })
  }

  async function openDetail(id: number) {
    if (openingId !== null) return
    setOpeningId(id)
    setDetailError('')
    try {
      onOpen(await replenishmentApi.recommendation(id))
    } catch (error) {
      setDetailError(decisionError(error, 'Could not load this recommendation. Try again.'))
    } finally {
      setOpeningId(null)
    }
  }

  return (
    <Paper component='section' elevation={0} aria-labelledby='exceptions-heading' sx={{ p: 3, borderRadius: 3 }}>
      <Stack spacing={2}>
        <Typography id='exceptions-heading' variant='h6' component='h2'>Inventory exceptions</Typography>
        <Box component='form' onSubmit={applyFilters}>
          <Grid container spacing={1.5}>
            <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
              <TextField label='Forecast run ID' size='small' value={scope.run_id} required fullWidth
                onChange={(event) => setScope({ ...scope, run_id: event.target.value })} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 2 }}>
              <TextField select label='Exception mode' size='small' value={scope.mode} fullWidth
                onChange={(event) => setScope({ ...scope, mode: event.target.value as RecommendationMode })}>
                <MenuItem value='simulation'>Simulation</MenuItem>
                <MenuItem value='live'>Live inventory</MenuItem>
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 2 }}>
              <TextField select label='Classification' size='small' value={classification} fullWidth
                onChange={(event) => setClassification(event.target.value as ExceptionClassification | '')}>
                <MenuItem value=''>All classifications</MenuItem>
                {Object.entries(classificationLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>{label}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, lg: 2 }}>
              <TextField select label='Review status' size='small' value={reviewStatus} fullWidth
                onChange={(event) => setReviewStatus(event.target.value as ReviewStatus | '')}>
                <MenuItem value=''>All review statuses</MenuItem>
                {Object.entries(reviewLabels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>{label}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, lg: 2 }}>
              <Button type='submit' variant='outlined' disabled={!scope.run_id.trim()} fullWidth sx={{ height: 40 }}>
                Load exceptions
              </Button>
            </Grid>
          </Grid>
        </Box>

        {!query && <Typography variant='body2' color='text.secondary'>Enter a saved forecast run ID to see its products.</Typography>}
        {query && !ready && <CircularProgress size={24} aria-label='Loading inventory exceptions' />}
        {ready && result.error && <Alert severity='error'>{result.error}</Alert>}
        {detailError && <Alert severity='error'>{detailError}</Alert>}
        {query && page && (
          <>
            <Typography variant='body2' color='text.secondary' role='status' sx={{ overflowWrap: 'anywhere' }}>
              {page.as_of_date ? `Review date ${formatDay(page.as_of_date)}` : 'Review date unavailable'}
              {' · '}{page.mode === 'live' ? 'Live inventory' : 'Simulation'}
              {' · '}{page.scope_total} SKUs · {page.missing_recommendations} without a recommendation
              {' · '}{page.run_id}
            </Typography>
            {page.total === 0 ? (
              <Alert severity='info'>{page.scope_total ? 'No products match these filters.' : 'No products were identified for this forecast run.'}</Alert>
            ) : (
              <>
                <TableContainer tabIndex={0} role='region' aria-label='Inventory exception results'>
                  <Table size='small' sx={{ minWidth: 830 }}>
                    <TableHead>
                      <TableRow>
                        <TableCell scope='col'>Product</TableCell>
                        <TableCell scope='col'>Classification and reasons</TableCell>
                        <TableCell scope='col'>First shortage</TableCell>
                        <TableCell scope='col' align='right'>Suggested units</TableCell>
                        <TableCell scope='col'>Review status</TableCell>
                        <TableCell scope='col' align='right'>Details</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {page.items.map((item) => (
                        <TableRow key={item.product_id} hover>
                          <TableCell component='th' scope='row'>
                            {item.product_name}
                            <Typography variant='body2' color='text.secondary'>{item.sku}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2' fontWeight={600}>{classificationLabels[item.classification]}</Typography>
                            {item.reasons.map((reason) => (
                              <Typography key={reason} variant='body2' color='text.secondary'>{reason}</Typography>
                            ))}
                          </TableCell>
                          <TableCell sx={{ whiteSpace: 'nowrap' }}>
                            {item.first_shortage_period_start ? formatDay(item.first_shortage_period_start) : '—'}
                            {item.first_shortage_quantity !== null && (
                              <Typography variant='body2'>{formatQuantity(item.first_shortage_quantity)} units short</Typography>
                            )}
                          </TableCell>
                          <TableCell align='right' sx={{ fontVariantNumeric: 'tabular-nums' }}>
                            {item.suggested_quantity === null ? '—' : formatQuantity(item.suggested_quantity)}
                          </TableCell>
                          <TableCell>
                            {item.review_status ? <Chip size='small' label={reviewLabels[item.review_status]} /> : '—'}
                          </TableCell>
                          <TableCell align='right'>
                            {item.recommendation_id !== null && (
                              <Button size='small' loading={openingId === item.recommendation_id} disabled={openingId !== null}
                                aria-label={`View recommendation for ${item.sku}`}
                                onClick={() => { if (item.recommendation_id !== null) void openDetail(item.recommendation_id) }}>
                                View
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                      {page.items.length === 0 && (
                        <TableRow><TableCell colSpan={6}>No results on this page. Load exceptions to return to page 1.</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
                <TablePagination component='div' count={page.total} rowsPerPage={pageSize} rowsPerPageOptions={[]}
                  page={Math.min(Math.floor(query.offset / pageSize), Math.ceil(page.total / pageSize) - 1)}
                  onPageChange={(_, next) => setQuery({ ...query, offset: next * pageSize })} />
              </>
            )}
          </>
        )}
      </Stack>
    </Paper>
  )
}
