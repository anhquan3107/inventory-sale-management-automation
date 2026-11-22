import { useState, type FormEvent } from 'react'
import { Alert, Button, InputAdornment, Paper, TextField } from '@mui/material'
import TuneOutlined from '@mui/icons-material/TuneOutlined'
import SaveOutlined from '@mui/icons-material/SaveOutlined'
import { decisionError, replenishmentApi } from '../../api/replenishment'
import type { PolicyValues, ReplenishmentPolicy } from '../../types/replenishment'
import { integerInRange, weekLabel } from './format'

const defaults: PolicyValues = {
  lead_time_weeks: 1,
  review_interval_weeks: 1,
  safety_stock: 0,
  minimum_order_quantity: 0,
  pack_size: 1,
}

const fields = [
  { key: 'lead_time_weeks', label: 'Lead time', min: 1, max: 25, unit: 'weeks' },
  { key: 'review_interval_weeks', label: 'Review interval', min: 1, max: 25, unit: 'weeks' },
  { key: 'safety_stock', label: 'Safety stock', min: 0, unit: 'units' },
  { key: 'minimum_order_quantity', label: 'Minimum order', min: 0, unit: 'units' },
  { key: 'pack_size', label: 'Pack size', min: 1, unit: 'units' },
] as const

type Draft = Record<keyof PolicyValues, string>

function draftFor(policy?: ReplenishmentPolicy): Draft {
  const values = policy ?? defaults
  return {
    lead_time_weeks: String(values.lead_time_weeks),
    review_interval_weeks: String(values.review_interval_weeks),
    safety_stock: String(values.safety_stock),
    minimum_order_quantity: String(values.minimum_order_quantity),
    pack_size: String(values.pack_size),
  }
}

interface Props {
  productId: number
  policy?: ReplenishmentPolicy
  onSave: (policy: ReplenishmentPolicy) => void
  onDirtyChange: (dirty: boolean) => void
}

export default function PolicyForm({ productId, policy, onSave, onDirtyChange }: Props) {
  const [draft, setDraft] = useState(() => draftFor(policy))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const original = draftFor(policy)
  const dirty = fields.some(({ key }) => draft[key] !== original[key])
  const protectionWeeks = Number(draft.lead_time_weeks) + Number(draft.review_interval_weeks)
  const validWeeks = integerInRange(draft.lead_time_weeks, 1, 25)
    && integerInRange(draft.review_interval_weeks, 1, 25)

  function change(key: keyof PolicyValues, value: string) {
    const next = { ...draft, [key]: value }
    setDraft(next)
    setSaved(false)
    setError('')
    onDirtyChange(fields.some((field) => next[field.key] !== original[field.key]))
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving || (policy && !dirty)) return
    const invalidField = fields.find(({ key, min, ...field }) => !integerInRange(
      draft[key], min, 'max' in field ? field.max : undefined,
    ))
    if (invalidField) {
      const range = 'max' in invalidField
        ? `between ${invalidField.min} and ${invalidField.max}`
        : `of at least ${invalidField.min}`
      setError(`${invalidField.label} requires a whole number ${range}.`)
      return
    }
    if (protectionWeeks > 26) {
      setError('Lead time and review interval must total 26 weeks or fewer.')
      return
    }

    setSaving(true)
    setError('')
    try {
      const result = await replenishmentApi.savePolicy(productId, {
        lead_time_weeks: Number(draft.lead_time_weeks),
        review_interval_weeks: Number(draft.review_interval_weeks),
        safety_stock: Number(draft.safety_stock),
        minimum_order_quantity: Number(draft.minimum_order_quantity),
        pack_size: Number(draft.pack_size),
      })
      onSave(result)
      setDraft(draftFor(result))
      onDirtyChange(false)
      setSaved(true)
    } catch (error) {
      setError(decisionError(error, 'Could not save the replenishment policy. Try again.'))
    } finally {
      setSaving(false)
    }
  }

  function reset() {
    setDraft(original)
    setError('')
    onDirtyChange(false)
  }

  return (
    <Paper component='section' variant='outlined' className='rp-card' aria-labelledby='policy-heading'>
      <div className='rp-card-heading'>
        <span className='rp-section-icon'><TuneOutlined fontSize='small' /></span>
        <div>
          <h2 id='policy-heading'>Replenishment policy</h2>
          <p>Set the timing and order constraints for this product.</p>
        </div>
      </div>
      <form onSubmit={save} className='rp-form'>
        <div className='rp-fields'>
          {fields.map(({ key, label, unit }) => (
            <TextField
              key={key}
              label={label}
              size='small'
              required
              disabled={saving}
              value={draft[key]}
              onChange={(event) => change(key, event.target.value)}
              slotProps={{
                htmlInput: { inputMode: 'numeric' },
                input: { endAdornment: <InputAdornment position='end'>{unit}</InputAdornment> },
              }}
            />
          ))}
        </div>
        <div className='rp-protection'>
          <div>
            <strong>Protection period</strong>
            <span>Lead time + review interval</span>
          </div>
          <b>{validWeeks ? weekLabel(protectionWeeks) : '—'}</b>
        </div>
        {error && <Alert severity='error'>{error}</Alert>}
        {saved && <Alert severity='success'>Policy saved as version {policy?.version}.</Alert>}
        <div className='rp-actions'>
          <Button type='submit' variant='contained' loading={saving} disabled={!!policy && !dirty} startIcon={<SaveOutlined />}>
            Save policy
          </Button>
          {dirty && <Button onClick={reset} disabled={saving}>Reset edits</Button>}
        </div>
      </form>
    </Paper>
  )
}
