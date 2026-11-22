import { useState, type FormEvent } from 'react'
import {
  Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControlLabel, TextField,
} from '@mui/material'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type { SalesCoverage } from '../../types/replenishment'
import { addDays, todayUtc } from './format'

interface Props {
  productId: number
  coverage?: SalesCoverage
  onSave: (coverage: SalesCoverage) => void
  onClose: () => void
}

export default function CoverageDialog({ productId, coverage, onSave, onClose }: Props) {
  const [from, setFrom] = useState(coverage?.observed_from ?? '')
  const [through, setThrough] = useState(coverage?.observed_through ?? '')
  const [source, setSource] = useState(coverage?.source ?? '')
  const [version, setVersion] = useState(coverage?.dataset_version ?? '')
  const [confirmed, setConfirmed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const yesterday = addDays(todayUtc(), -1)
  const changed = coverage && (from !== coverage.observed_from || through !== coverage.observed_through
    || source.trim() !== coverage.source)

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving || !confirmed) return
    if (!source.trim() || !version.trim()) {
      setError('Enter the sales source and dataset version.')
      return
    }
    if (!from || !through || through < from || through > yesterday) {
      setError('Enter a continuous date range that ends on a completed day.')
      return
    }
    if (changed && version.trim() === coverage?.dataset_version) {
      setError('Enter a new dataset version for the updated coverage.')
      return
    }

    setSaving(true)
    setError('')
    try {
      onSave(await replenishmentApi.saveCoverage(productId, {
        observed_from: from,
        observed_through: through,
        source: source.trim(),
        dataset_version: version.trim(),
        configuration: coverage?.configuration ?? {},
      }))
      onClose()
    } catch (error) {
      setError(decisionError(error, 'Could not save sales coverage. Try again.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onClose={saving ? undefined : onClose} fullWidth maxWidth='sm' aria-labelledby='coverage-title'>
      <form onSubmit={save}>
        <DialogTitle id='coverage-title'>Sales coverage</DialogTitle>
        <DialogContent dividers>
          <div className='rp-form'>
            <p className='rp-muted rp-no-margin'>Declare a continuous period with complete sales records. The forecast treats days without transactions in this period as zero-sales days.</p>
            <div className='rp-fields'>
              <TextField label='First observed day (UTC)' type='date' required disabled={saving}
                value={from} onChange={(event) => setFrom(event.target.value)}
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: through || yesterday } }} />
              <TextField label='Last observed day (UTC)' type='date' required disabled={saving}
                value={through} onChange={(event) => setThrough(event.target.value)}
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: from, max: yesterday } }} />
              <TextField label='Sales source' required disabled={saving} value={source}
                onChange={(event) => setSource(event.target.value)} slotProps={{ htmlInput: { maxLength: 80 } }} />
              <TextField label='Dataset version' required disabled={saving} value={version}
                onChange={(event) => setVersion(event.target.value)} slotProps={{ htmlInput: { maxLength: 100 } }} />
            </div>
            <FormControlLabel
              control={<Checkbox checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={saving} />}
              label='I confirm sales records are complete for every day in this period.'
            />
            {error && <Alert severity='error'>{error}</Alert>}
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type='submit' variant='contained' loading={saving} disabled={!confirmed}>Save coverage</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
