import { useEffect, useState } from 'react'
import {
  Alert, Button, Chip, CircularProgress, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography,
} from '@mui/material'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type { ProductResponse } from '../../types/product'
import type { Recommendation } from '../../types/replenishment'
import { formatDay, formatQuantity } from './format'

const pageSize = 10

interface Props {
  products: ProductResponse[]
  reviewed: Record<number, Recommendation>
  onOpen: (recommendation: Recommendation) => void
}

interface Page {
  key: string
  items: Recommendation[]
  error: string
}

export default function RecommendationHistory({ products, reviewed, onOpen }: Props) {
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [page, setPage] = useState<Page | null>(null)
  const key = `${offset}:${attempt}`
  const ready = page?.key === key
  const items = ready ? page.items.slice(0, pageSize).map((item) => reviewed[item.id] ?? item) : []
  const hasNext = ready && page.items.length > pageSize
  const error = ready && page.error

  useEffect(() => {
    let ignore = false
    replenishmentApi.recommendations(pageSize + 1, offset)
      .then((items) => { if (!ignore) setPage({ key, items, error: '' }) })
      .catch((error) => {
        if (!ignore) setPage({
          key, items: [], error: decisionError(error, 'Could not load recommendations. Try again.'),
        })
      })
    return () => { ignore = true }
  }, [key, offset])

  return (
    <Paper component='section' elevation={0} aria-labelledby='history-heading' sx={{ p: 3, borderRadius: 3 }}>
      <Stack direction='row' justifyContent='space-between' alignItems='center' useFlexGap flexWrap='wrap' spacing={1} sx={{ mb: 2 }}>
        <Typography id='history-heading' variant='h6' component='h2'>Recommendation history</Typography>
        <Button variant='outlined' disabled={!ready} onClick={() => setAttempt((count) => count + 1)}>Refresh</Button>
      </Stack>

      {!ready ? (
        <Stack direction='row' justifyContent='center' sx={{ py: 4 }} role='status' aria-label='Loading recommendations'>
          <CircularProgress size={24} />
        </Stack>
      ) : error ? (
        <Alert severity='error' action={<Button color='inherit' onClick={() => setAttempt((count) => count + 1)}>Retry</Button>}>
          {error}
        </Alert>
      ) : (
        <>
          <TableContainer>
            <Table size='small'>
              <TableHead>
                <TableRow>
                  <TableCell scope='col'>Product</TableCell>
                  <TableCell scope='col'>SKU</TableCell>
                  <TableCell scope='col'>Review date</TableCell>
                  <TableCell scope='col'>Mode</TableCell>
                  <TableCell scope='col' align='right'>Suggested order</TableCell>
                  <TableCell scope='col'>Status</TableCell>
                  <TableCell scope='col' align='right'>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} sx={{ color: 'text.secondary' }}>
                      {offset ? 'No recommendations on this page.' : 'No recommendations yet.'}
                    </TableCell>
                  </TableRow>
                ) : items.map((item) => {
                  const product = products.find((product) => product.id === item.product_id)
                  return (
                    <TableRow key={item.id} hover>
                      <TableCell component='th' scope='row'>{product?.name ?? `Product #${item.product_id}`}</TableCell>
                      <TableCell>{product?.sku ?? '—'}</TableCell>
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>{item.snapshot.decision_date ? formatDay(item.snapshot.decision_date) : '—'}</TableCell>
                      <TableCell>{item.snapshot.mode === 'live' ? 'Live' : item.snapshot.mode === 'simulation' ? 'Simulation' : '—'}</TableCell>
                      <TableCell align='right'>
                        {formatQuantity(item.suggested_quantity)} units
                        {item.snapshot.result?.stockout_risk && (
                          <Typography variant='body2' sx={{ fontWeight: 600 }}>Stockout risk</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip label={item.status} size='small' variant={item.status === 'pending' ? 'outlined' : 'filled'}
                          sx={{ textTransform: 'capitalize' }} />
                      </TableCell>
                      <TableCell align='right'>
                        <Button size='small' onClick={() => onOpen(item)} aria-label={`View recommendation ${item.id}`}>
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
          {(hasNext || offset > 0) && (
            <Stack direction='row' alignItems='center' justifyContent='flex-end' spacing={1} sx={{ mt: 2 }}>
              <Typography variant='body2' color='text.secondary' sx={{ flexGrow: 1 }}>
                {items.length ? `Showing ${offset + 1}–${offset + items.length}` : 'No results'}
              </Typography>
              <Button size='small' disabled={!offset} onClick={() => setOffset(offset - pageSize)}>Previous</Button>
              <Button size='small' disabled={!hasNext} onClick={() => setOffset(offset + pageSize)}>Next</Button>
            </Stack>
          )}
        </>
      )}
    </Paper>
  )
}
