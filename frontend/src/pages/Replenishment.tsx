import { useEffect, useState } from 'react'
import {
  Alert, Autocomplete, Button, Chip, CircularProgress, Paper, Tab, Tabs, TextField,
  ThemeProvider, Typography, createFilterOptions, createTheme,
} from '@mui/material'
import AccountTreeOutlined from '@mui/icons-material/AccountTreeOutlined'
import EventRepeatOutlined from '@mui/icons-material/EventRepeatOutlined'
import FactCheckOutlined from '@mui/icons-material/FactCheckOutlined'
import Inventory2Outlined from '@mui/icons-material/Inventory2Outlined'
import InfoOutlined from '@mui/icons-material/InfoOutlined'
import { productsApi } from '../api/products'
import { decisionError, replenishmentApi } from '../api/replenishment'
import { useAuth } from '../hooks/use-auth'
import { theme } from '../theme'
import type { ProductResponse } from '../types/product'
import type { Recommendation, ReplenishmentPolicy, SalesCoverage, WeeklyForecast } from '../types/replenishment'
import PolicyForm from '../components/replenishment/PolicyForm'
import ForecastForm from '../components/replenishment/ForecastForm'
import ScenarioForm from '../components/replenishment/ScenarioForm'
import RecommendationHistory from '../components/replenishment/RecommendationHistory'
import RecommendationDetail from '../components/replenishment/RecommendationDetail'
import { weekLabel } from '../components/replenishment/format'
import './Replenishment.css'

const workspaceTheme = createTheme(theme, {
  components: {
    MuiAlert: {
      styleOverrides: {
        standard: {
          color: theme.palette.text.primary,
          backgroundColor: theme.palette.grey[100],
          border: `1px solid ${theme.palette.divider}`,
          '& .MuiAlert-icon': { color: theme.palette.text.primary },
        },
      },
    },
  },
})

const filterProducts = createFilterOptions<ProductResponse>({
  stringify: (product) => `${product.name} ${product.sku}`,
})

interface PlanningData {
  products: ProductResponse[]
  policies: ReplenishmentPolicy[]
  coverage: SalesCoverage[]
}

interface PlanningProps {
  product: ProductResponse
  policy?: ReplenishmentPolicy
  coverage?: SalesCoverage
  onSavePolicy: (policy: ReplenishmentPolicy) => void
  onSaveCoverage: (coverage: SalesCoverage) => void
  onGenerate: (result: Recommendation) => void
}

function Planning({ product, policy, coverage, onSavePolicy, onSaveCoverage, onGenerate }: PlanningProps) {
  const [policyDirty, setPolicyDirty] = useState(false)
  const [forecast, setForecast] = useState<WeeklyForecast | null>(null)
  const protectionWeeks = policy ? policy.lead_time_weeks + policy.review_interval_weeks : undefined

  return (
    <div className='rp-planning'>
      <div className='rp-column'>
        <PolicyForm productId={product.id} policy={policy} onSave={onSavePolicy} onDirtyChange={setPolicyDirty} />
        <aside className='rp-guide' aria-labelledby='guide-heading'>
          <AccountTreeOutlined fontSize='small' aria-hidden='true' />
          <div>
            <h2 id='guide-heading'>How the policy works</h2>
            <p>The target covers forecast demand during lead time and the time until the next review, plus safety stock.</p>
            <p>When inventory position falls short of the target, the suggested order meets the minimum and rounds up to a full pack.</p>
          </div>
        </aside>
      </div>
      <div className='rp-column'>
        <ForecastForm productId={product.id} protectionWeeks={protectionWeeks} policyDirty={policyDirty}
          coverage={coverage} forecast={forecast} onCoverage={onSaveCoverage} onForecast={setForecast} />
        <ScenarioForm productId={product.id} policy={policy} policyDirty={policyDirty} forecast={forecast}
          onGenerate={onGenerate} />
      </div>
    </div>
  )
}

function ReplenishmentWorkspace() {
  const [tab, setTab] = useState('planning')
  const [productId, setProductId] = useState<number | null>(null)
  const [data, setData] = useState<PlanningData | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [detail, setDetail] = useState<Recommendation | null>(null)
  const [reviewed, setReviewed] = useState<Record<number, Recommendation>>({})

  useEffect(() => {
    let ignore = false
    Promise.all([productsApi.list(), replenishmentApi.policies(), replenishmentApi.coverage()])
      .then(([products, policies, coverage]) => {
        if (!ignore) setData({ products, policies, coverage })
      })
      .catch((error) => {
        if (!ignore) setError(decisionError(error, 'Could not load the planning workspace. Try again.'))
      })
    return () => { ignore = true }
  }, [attempt])

  const products = data?.products ?? []
  const activeProducts = products.filter((product) => product.is_active).sort((a, b) => a.name.localeCompare(b.name))
  const product = activeProducts.find((item) => item.id === productId)
    ?? activeProducts[0]
  const policy = data?.policies.find((item) => item.product_id === product?.id)
  const coverage = data?.coverage.find((item) => item.product_id === product?.id)
  const detailProduct = products.find((item) => item.id === detail?.product_id)

  function savePolicy(policy: ReplenishmentPolicy) {
    setData((current) => current && ({
      ...current,
      policies: [...current.policies.filter((item) => item.product_id !== policy.product_id), policy],
    }))
  }

  function saveCoverage(coverage: SalesCoverage) {
    setData((current) => current && ({
      ...current,
      coverage: [...current.coverage.filter((item) => item.product_id !== coverage.product_id), coverage],
    }))
  }

  return (
    <>
      <div className='rp-workspace'>
        <header className='rp-header'>
          <div>
            <Typography variant='h5' component='h1' sx={{ mb: 0.5 }}>Replenishment</Typography>
            <Typography variant='body2' color='text.secondary'>
              Plan weekly stock orders using product policies and forecast demand.
            </Typography>
          </div>
          <Chip size='small' variant='outlined' icon={<InfoOutlined />} label='Advisory decisions only' />
        </header>

        <Tabs className='rp-tabs' aria-label='Replenishment workspace' value={tab}
          onChange={(_, value: string) => setTab(value)}>
          <Tab id='rp-planning-tab' aria-controls='rp-planning-panel' icon={<EventRepeatOutlined />} iconPosition='start' label='Planning' value='planning' />
          <Tab id='rp-history-tab' aria-controls='rp-history-panel' icon={<FactCheckOutlined />} iconPosition='start' label='Recommendations' value='history' />
        </Tabs>

        <div role='tabpanel' id='rp-planning-panel' aria-labelledby='rp-planning-tab' hidden={tab !== 'planning'}>
          {error ? (
            <Alert severity='error' action={
              <Button color='inherit' onClick={() => { setError(''); setAttempt((count) => count + 1) }}>Retry</Button>
            }>{error}</Alert>
          ) : !data ? (
            <div className='rp-card rp-empty' role='status'><CircularProgress size={24} /> Loading planning workspace…</div>
          ) : !product ? (
            <div className='rp-card rp-empty'>
              <Inventory2Outlined />
              <strong>No active products</strong>
              <p>Activate a product to configure its replenishment policy.</p>
            </div>
          ) : (
            <>
              <Paper component='section' variant='outlined' className='rp-product-strip' aria-label='Product context'>
                <div className='rp-product-picker'>
                  <span className='rp-product-icon'><Inventory2Outlined fontSize='small' /></span>
                  <Autocomplete
                    options={activeProducts}
                    value={product}
                    onChange={(_, selected) => { if (selected) setProductId(selected.id) }}
                    disableClearable
                    isOptionEqualToValue={(option, value) => option.id === value.id}
                    filterOptions={filterProducts}
                    getOptionLabel={(option) => option.name}
                    getOptionKey={(option) => option.id}
                    renderOption={({ key, ...props }, option) => (
                      <li key={key} {...props}><span className='rp-product-option'>{option.name}<small>{option.sku}</small></span></li>
                    )}
                    size='small'
                    fullWidth
                    renderInput={(params) => <TextField {...params} label='Planning product' helperText={product.sku} />}
                  />
                </div>
                <dl className='rp-product-summary'>
                  <div>
                    <dt>Saved policy</dt>
                    <dd><span className={policy ? 'rp-badge' : 'rp-badge rp-badge-strong'}>{policy ? `Version ${policy.version}` : 'Setup required'}</span></dd>
                  </div>
                  <div>
                    <dt>Protection period</dt>
                    <dd>{policy ? weekLabel(policy.lead_time_weeks + policy.review_interval_weeks) : '—'}</dd>
                  </div>
                  <div>
                    <dt>Sales coverage</dt>
                    <dd>{coverage ? 'Declared' : 'Not declared'}</dd>
                  </div>
                </dl>
              </Paper>
              <Planning key={product.id} product={product} policy={policy} coverage={coverage}
                onSavePolicy={savePolicy} onSaveCoverage={saveCoverage} onGenerate={setDetail} />
            </>
          )}
        </div>
        <div role='tabpanel' id='rp-history-panel' aria-labelledby='rp-history-tab' hidden={tab !== 'history'}>
          {tab === 'history' && (
            <RecommendationHistory products={products} reviewed={reviewed}
              onOpen={setDetail} onPlan={() => setTab('planning')} />
          )}
        </div>
      </div>
      {detail && (
        <RecommendationDetail
          key={detail.id}
          recommendation={detail}
          productLabel={detailProduct ? `${detailProduct.name} · ${detailProduct.sku}` : `Product #${detail.product_id}`}
          onUpdate={(result) => {
            setDetail(result)
            setReviewed((current) => ({ ...current, [result.id]: result }))
          }}
          onClose={() => setDetail(null)}
        />
      )}
    </>
  )
}

export default function Replenishment() {
  const { user } = useAuth()
  return (
    <ThemeProvider theme={workspaceTheme}>
      {user?.role === 'admin'
        ? <ReplenishmentWorkspace />
        : <Alert severity='error'>Replenishment requires administrator access.</Alert>}
    </ThemeProvider>
  )
}
