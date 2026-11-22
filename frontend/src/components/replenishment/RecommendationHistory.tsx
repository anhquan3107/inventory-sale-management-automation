import { useEffect, useState } from 'react'
import { Alert, Button, CircularProgress, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material'
import FactCheckOutlined from '@mui/icons-material/FactCheckOutlined'
import HistoryOutlined from '@mui/icons-material/HistoryOutlined'
import ReplayOutlined from '@mui/icons-material/ReplayOutlined'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type { ProductResponse } from '../../types/product'
import type { Recommendation } from '../../types/replenishment'
import { formatDay, formatQuantity } from './format'

const pageSize = 10

interface Props {
  products: ProductResponse[]
  reviewed: Record<number, Recommendation>
  onOpen: (recommendation: Recommendation) => void
  onPlan: () => void
}

interface Page {
  key: string
  items: Recommendation[]
  error: string
}

export default function RecommendationHistory({ products, reviewed, onOpen, onPlan }: Props) {
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
    <Paper component='section' variant='outlined' className='rp-card' aria-labelledby='history-heading'>
      <div className='rp-card-heading rp-history-heading'>
        <span className='rp-section-icon'><HistoryOutlined fontSize='small' /></span>
        <div>
          <h2 id='history-heading'>Recommendation history</h2>
          <p>Review pending recommendations and track recorded decisions.</p>
        </div>
        <Button startIcon={<ReplayOutlined />} disabled={!ready} onClick={() => setAttempt((count) => count + 1)}>Refresh</Button>
      </div>
      {!ready ? (
        <div className='rp-empty' role='status'><CircularProgress size={24} /> Loading recommendations…</div>
      ) : error ? (
        <Alert severity='error' action={<Button color='inherit' onClick={() => setAttempt((count) => count + 1)}>Retry</Button>}>{error}</Alert>
      ) : items.length === 0 && offset === 0 ? (
        <div className='rp-empty'>
          <FactCheckOutlined />
          <strong>No recommendations yet</strong>
          <p>Generate an order recommendation to start your review history.</p>
          <Button onClick={onPlan} variant='outlined'>Open planning</Button>
        </div>
      ) : (
        <>
          <TableContainer className='rp-table-wrap'>
            <Table className='rp-table'>
              <TableHead>
                <TableRow>
                  <TableCell scope='col'>Product</TableCell><TableCell scope='col'>Review date</TableCell><TableCell scope='col'>Mode</TableCell>
                  <TableCell scope='col'>Suggested order</TableCell><TableCell scope='col'>Status</TableCell><TableCell scope='col'>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => {
                  const product = products.find((product) => product.id === item.product_id)
                  return (
                    <TableRow key={item.id}>
                      <TableCell component='th' scope='row'>
                        <strong>{product?.name ?? `Product #${item.product_id}`}</strong>
                        <small>{product?.sku ? `${product.sku} · ` : ''}#{item.id}</small>
                      </TableCell>
                      <TableCell>{formatDay(item.snapshot.decision_date)}</TableCell>
                      <TableCell>{item.snapshot.mode === 'live' ? 'Live' : 'Simulation'}</TableCell>
                      <TableCell>
                        {formatQuantity(item.suggested_quantity)} units
                        {item.snapshot.result.stockout_risk && <small className='rp-stock-negative'>Stockout risk</small>}
                      </TableCell>
                      <TableCell><span className={`rp-badge rp-${item.status}`}>{item.status}</span></TableCell>
                      <TableCell><Button size='small' onClick={() => onOpen(item)} aria-label={`View recommendation ${item.id}`}>View</Button></TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
          <div className='rp-pagination'>
            <span className='rp-small'>{items.length ? `Showing ${offset + 1}–${offset + items.length}` : 'No recommendations on this page'}</span>
            <Button size='small' disabled={!offset} onClick={() => setOffset(offset - pageSize)}>Previous</Button>
            <Button size='small' disabled={!hasNext} onClick={() => setOffset(offset + pageSize)}>Next</Button>
          </div>
        </>
      )}
    </Paper>
  )
}
