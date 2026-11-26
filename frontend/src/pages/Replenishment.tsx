import { useEffect, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Chip, CircularProgress, Grid, Paper, Stack,
  TextField, ThemeProvider, Typography, createFilterOptions, createTheme,
} from '@mui/material'
import { productsApi } from '../api/products'
import { decisionError, replenishmentApi } from '../api/replenishment'
import { useAuth } from '../hooks/use-auth'
import { theme } from '../theme'
import type { ProductResponse } from '../types/product'
import type { Recommendation, ReplenishmentPolicy, SalesCoverage, WeeklyForecast } from '../types/replenishment'
import PolicyForm from '../components/replenishment/PolicyForm'
import ForecastForm from '../components/replenishment/ForecastForm'
import SavedForecastForm from '../components/replenishment/SavedForecastForm'
import ScenarioForm from '../components/replenishment/ScenarioForm'
import RecommendationHistory from '../components/replenishment/RecommendationHistory'
import RecommendationDetail from '../components/replenishment/RecommendationDetail'
import ExceptionWorkspace from '../components/replenishment/ExceptionWorkspace'

const workspaceTheme = createTheme(theme, {
  palette: {
    error: {
      main: theme.palette.text.primary,
      light: theme.palette.grey[500],
      dark: theme.palette.grey[900],
      contrastText: theme.palette.common.white,
    },
  },
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
  decisions: boolean
  products: ProductResponse[]
  policies: ReplenishmentPolicy[]
  coverage: SalesCoverage[]
  onSavePolicy: (policy: ReplenishmentPolicy) => void
  onSaveCoverage: (coverage: SalesCoverage) => void
  onGenerate: (result: Recommendation) => void
}

interface PlanningSelection {
  productId: number
  revision: number
  policyDirty: boolean
  forecast: WeeklyForecast | null
}

function Planning({ decisions, products, policies, coverage, onSavePolicy, onSaveCoverage, onGenerate }: PlanningProps) {
  const [selection, setSelection] = useState<PlanningSelection>({
    productId: products[0].id,
    revision: 0,
    policyDirty: false,
    forecast: null,
  })
  const { productId, revision, policyDirty, forecast } = selection
  const product = products.find((item) => item.id === productId) ?? products[0]
  const policy = policies.find((item) => item.product_id === product.id)
  const productCoverage = coverage.find((item) => item.product_id === product.id)
  const protectionWeeks = policy ? policy.lead_time_weeks + policy.review_interval_weeks : undefined

  function updateSelection(values: Partial<Pick<PlanningSelection, 'policyDirty' | 'forecast'>>) {
    setSelection((current) => current.revision === revision ? { ...current, ...values } : current)
  }

  return (
    <>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Paper
          component='section'
          elevation={0}
          aria-labelledby='policy-heading'
          sx={{ p: 3, borderRadius: 3 }}
        >
          <Stack
            direction='row'
            justifyContent='space-between'
            alignItems='center'
            useFlexGap
            flexWrap='wrap'
            spacing={1}
            sx={{ mb: 2 }}
          >
            <Typography id='policy-heading' variant='h6' component='h2'>Replenishment policy</Typography>
            <Chip size='small' label={policy ? `Version ${policy.version}` : 'Setup required'} />
          </Stack>

          <Stack spacing={1.5}>
            <Autocomplete
              options={products}
              value={product}
              onChange={(_, selected) => {
                setSelection((current) => current.productId === selected.id ? current : {
                  productId: selected.id,
                  revision: current.revision + 1,
                  policyDirty: false,
                  forecast: null,
                })
              }}
              disableClearable
              isOptionEqualToValue={(option, value) => option.id === value.id}
              filterOptions={filterProducts}
              getOptionLabel={(option) => option.name}
              getOptionKey={(option) => option.id}
              renderOption={({ key, ...props }, option) => (
                <Box component='li' key={key} {...props}>
                  <Box>
                    {option.name}
                    <Typography variant='body2' color='text.secondary'>{option.sku}</Typography>
                  </Box>
                </Box>
              )}
              size='small'
              fullWidth
              renderInput={(params) => <TextField {...params} label='Planning product' helperText={product.sku} />}
            />
            <PolicyForm
              key={product.id}
              productId={product.id}
              policy={policy}
              onSave={onSavePolicy}
              onDirtyChange={(policyDirty) => updateSelection({ policyDirty })}
            />
          </Stack>
        </Paper>
      </Grid>

      <Grid size={{ xs: 12, lg: 6 }}>
        {decisions ? (
          <SavedForecastForm
            key={product.id}
            productId={product.id}
            protectionWeeks={protectionWeeks}
            forecast={forecast}
            onForecast={(forecast) => updateSelection({ forecast })}
          />
        ) : (
          <ForecastForm
            key={product.id}
            productId={product.id}
            protectionWeeks={protectionWeeks}
            policyDirty={policyDirty}
            coverage={productCoverage}
            forecast={forecast}
            onCoverage={onSaveCoverage}
            onForecast={(forecast) => updateSelection({ forecast })}
          />
        )}
      </Grid>

      <Grid size={12}>
        <ScenarioForm
          key={product.id}
          productId={product.id}
          policy={policy}
          policyDirty={policyDirty}
          forecast={forecast}
          onGenerate={onGenerate}
        />
      </Grid>
    </>
  )
}

function ReplenishmentWorkspace({ decisions }: { decisions: boolean }) {
  const [data, setData] = useState<PlanningData | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [detail, setDetail] = useState<Recommendation | null>(null)
  const [lastGenerated, setLastGenerated] = useState<Recommendation>()
  const [reviewed, setReviewed] = useState<Record<number, Recommendation>>({})

  useEffect(() => {
    let ignore = false
    Promise.all([productsApi.list(), replenishmentApi.policies(), decisions ? [] : replenishmentApi.coverage()])
      .then(([products, policies, coverage]) => {
        if (!ignore) setData({ products, policies, coverage })
      })
      .catch((error) => {
        if (!ignore) setError(decisionError(error, 'Could not load the planning workspace. Try again.'))
      })
    return () => { ignore = true }
  }, [attempt, decisions])

  const products = data?.products ?? []
  const activeProducts = products.filter((product) => product.is_active).sort((a, b) => a.name.localeCompare(b.name))
  const detailProduct = products.find((item) => item.id === detail?.product_id)
  const generatedScope = lastGenerated && { run_id: lastGenerated.snapshot.request.run_id, mode: lastGenerated.snapshot.mode }

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
    <Box>
      <Paper
        component='header'
        elevation={0}
        sx={{
          p: 3,
          mb: 3,
          borderRadius: 3,
          background: 'linear-gradient(180deg, #ffffff 0%, #fbfbfb 100%)',
        }}
      >
        <Stack
          direction='row'
          justifyContent='space-between'
          alignItems='center'
          useFlexGap
          flexWrap='wrap'
          spacing={1}
        >
          <Box>
            <Typography variant='h5' component='h1' sx={{ mb: 0.5 }}>
              {decisions ? 'Inventory decisions' : 'Replenishment'}
            </Typography>
            <Typography variant='body2' color='text.secondary'>
              {decisions
                ? 'Review projected shortages and decide how much to replenish.'
                : 'Plan weekly stock orders using product policies and forecast demand.'}
            </Typography>
          </Box>
          <Chip size='small' label='Advisory decisions only' />
        </Stack>
      </Paper>

      <Grid container spacing={3}>
        {decisions && (
          <Grid size={12}>
            <ExceptionWorkspace
              key={generatedScope && `${generatedScope.run_id}:${generatedScope.mode}`}
              initialScope={generatedScope}
              refreshKey={`${lastGenerated?.id}:${Object.keys(reviewed).length}`}
              onOpen={setDetail}
            />
          </Grid>
        )}
        {error ? (
          <Grid size={12}>
            <Alert
              severity='error'
              action={
                <Button
                  color='inherit'
                  onClick={() => {
                    setError('')
                    setAttempt((count) => count + 1)
                  }}
                >
                  Retry
                </Button>
              }
            >
              {error}
            </Alert>
          </Grid>
        ) : !data || !activeProducts.length ? (
          <Grid size={12}>
            <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
              {data ? (
                <Typography color='text.secondary'>Activate a product to configure its replenishment policy.</Typography>
              ) : (
                <Stack
                  direction='row'
                  justifyContent='center'
                  sx={{ py: 4 }}
                  role='status'
                  aria-label='Loading replenishment'
                >
                  <CircularProgress size={24} />
                </Stack>
              )}
            </Paper>
          </Grid>
        ) : (
          <Planning
            decisions={decisions}
            products={activeProducts}
            policies={data.policies}
            coverage={data.coverage}
            onSavePolicy={savePolicy}
            onSaveCoverage={saveCoverage}
            onGenerate={(result) => {
              setDetail(result)
              setLastGenerated(result)
            }}
          />
        )}

        <Grid size={12}>
          <RecommendationHistory
            key={lastGenerated?.id}
            products={products}
            reviewed={reviewed}
            onOpen={setDetail}
          />
        </Grid>
      </Grid>

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
    </Box>
  )
}

export default function Replenishment({ decisions = false }: { decisions?: boolean }) {
  const { user } = useAuth()
  return (
    <ThemeProvider theme={workspaceTheme}>
      {user?.role === 'admin'
        ? <ReplenishmentWorkspace key={String(decisions)} decisions={decisions} />
        : <Alert severity='error'>Inventory decisions require administrator access.</Alert>}
    </ThemeProvider>
  )
}
