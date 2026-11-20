import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { inventoryApi } from '../api/inventory'
import { inventoryLogApi } from '../api/inventory-log'
import { productsApi } from '../api/products'
import type {
  InventoryLogResponse,
  InventoryLogType,
  InventoryResponse,
} from '../types/inventory'
import type { ProductResponse } from '../types/product'

const LOG_TYPE_OPTIONS: InventoryLogType[] = [
  'INIT',
  'SALE',
  'RESTOCK',
  'ADJUSTMENT',
  'RETURN',
]

const toErrorMessage = (error: unknown): string => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } })
      .response
    if (response?.data?.detail) {
      return response.data.detail
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong. Please try again.'
}

const Inventory = () => {
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [inventoryItems, setInventoryItems] = useState<InventoryResponse[]>([])
  const [inventoryLogs, setInventoryLogs] = useState<InventoryLogResponse[]>([])

  const [loadingInventory, setLoadingInventory] = useState(false)
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [submittingInit, setSubmittingInit] = useState(false)
  const [submittingAdjust, setSubmittingAdjust] = useState(false)
  const [lookingUp, setLookingUp] = useState(false)

  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [initProductId, setInitProductId] = useState('')
  const [initQuantity, setInitQuantity] = useState('')

  const [adjustProductId, setAdjustProductId] = useState('')
  const [adjustQuantity, setAdjustQuantity] = useState('')

  const [lookupProductId, setLookupProductId] = useState('')
  const [lookupResult, setLookupResult] = useState<InventoryResponse | null>(
    null,
  )

  const [logProductFilter, setLogProductFilter] = useState('')
  const [logTypeFilter, setLogTypeFilter] = useState('')
  const [logLimit, setLogLimit] = useState('100')

  const productNameById = useMemo(() => {
    const map = new Map<number, string>()
    products.forEach((product) => {
      map.set(product.id, product.name)
    })
    return map
  }, [products])

  const productById = useMemo(() => {
    const map = new Map<number, ProductResponse>()
    products.forEach((product) => {
      map.set(product.id, product)
    })
    return map
  }, [products])

  const loadInventory = async (): Promise<void> => {
    setLoadingInventory(true)
    try {
      const data = await inventoryApi.list()
      setInventoryItems(data)
    } finally {
      setLoadingInventory(false)
    }
  }

  const loadLogs = async (): Promise<void> => {
    setLoadingLogs(true)

    try {
      const limitValue = Number(logLimit)
      const params = {
        product_id: logProductFilter ? Number(logProductFilter) : undefined,
        log_type: logTypeFilter
          ? (logTypeFilter as InventoryLogType)
          : undefined,
        limit:
          Number.isNaN(limitValue) || limitValue <= 0
            ? 100
            : Math.min(limitValue, 500),
      }

      const data = await inventoryLogApi.list(params)
      setInventoryLogs(data)
    } finally {
      setLoadingLogs(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      setErrorMessage('')

      try {
        const [productsData, inventoryData, logData] = await Promise.all([
          productsApi.list(),
          inventoryApi.list(),
          inventoryLogApi.list({ limit: 100 }),
        ])

        setProducts(productsData)
        setInventoryItems(inventoryData)
        setInventoryLogs(logData)
      } catch (error) {
        setErrorMessage(toErrorMessage(error))
      }
    }

    void initialize()
  }, [])

  const handleInitInventory = async (): Promise<void> => {
    const productId = Number(initProductId)
    const quantity = Number(initQuantity)

    if (!initProductId || Number.isNaN(productId)) {
      setErrorMessage('Please select a product for initialization.')
      return
    }

    if (Number.isNaN(quantity) || quantity < 0) {
      setErrorMessage(
        'Initial quantity must be a number greater than or equal to 0.',
      )
      return
    }

    setErrorMessage('')
    setSuccessMessage('')
    setSubmittingInit(true)

    try {
      await inventoryApi.init({
        product_id: productId,
        quantity,
      })
      setSuccessMessage('Inventory initialized successfully.')
      setInitQuantity('')
      await Promise.all([loadInventory(), loadLogs()])
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setSubmittingInit(false)
    }
  }

  const handleAdjustInventory = async (): Promise<void> => {
    const productId = Number(adjustProductId)
    const changeQuantity = Number(adjustQuantity)

    if (!adjustProductId || Number.isNaN(productId)) {
      setErrorMessage('Please select a product for adjustment.')
      return
    }

    if (Number.isNaN(changeQuantity) || changeQuantity === 0) {
      setErrorMessage('Adjustment quantity must be a non-zero number.')
      return
    }

    setErrorMessage('')
    setSuccessMessage('')
    setSubmittingAdjust(true)

    try {
      await inventoryApi.adjust({
        product_id: productId,
        change_quantity: changeQuantity,
      })
      setSuccessMessage('Inventory adjusted successfully.')
      setAdjustQuantity('')
      await Promise.all([loadInventory(), loadLogs()])
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setSubmittingAdjust(false)
    }
  }

  const handleLookupInventory = async (): Promise<void> => {
    const productId = Number(lookupProductId)

    if (!lookupProductId || Number.isNaN(productId)) {
      setErrorMessage('Please select a product to check inventory detail.')
      return
    }

    setErrorMessage('')
    setSuccessMessage('')
    setLookingUp(true)

    try {
      const data = await inventoryApi.getByProduct(productId)
      setLookupResult(data)
    } catch (error) {
      setLookupResult(null)
      setErrorMessage(toErrorMessage(error))
    } finally {
      setLookingUp(false)
    }
  }

  const handleApplyLogFilters = async (): Promise<void> => {
    setErrorMessage('')
    setSuccessMessage('')

    try {
      await loadLogs()
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    }
  }

  return (
    <Box>
      <Paper
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
        >
          <Box>
            <Typography variant='h5' sx={{ mb: 0.5 }}>
              Inventory
            </Typography>
            <Typography variant='body2' sx={{ color: '#666666' }}>
              Initialize, adjust, and monitor stock movement in real time.
            </Typography>
          </Box>

          <Stack direction='row' spacing={1}>
            <Chip label={`Items: ${inventoryItems.length}`} size='small' />
            <Chip label={`Logs: ${inventoryLogs.length}`} size='small' />
          </Stack>
        </Stack>
      </Paper>

      <Stack spacing={2} sx={{ mb: 3 }}>
        {errorMessage && <Alert severity='error'>{errorMessage}</Alert>}
        {successMessage && <Alert severity='success'>{successMessage}</Alert>}
      </Stack>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Inventory Actions
            </Typography>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Typography variant='body2' sx={{ fontWeight: 600, mb: 1 }}>
                  Initialize Inventory
                </Typography>

                <Stack spacing={1.5}>
                  <TextField
                    select
                    label='Product'
                    value={initProductId}
                    onChange={(event) => setInitProductId(event.target.value)}
                    fullWidth
                    size='small'
                  >
                    {products.map((product) => (
                      <MenuItem key={product.id} value={String(product.id)}>
                        {product.name}
                      </MenuItem>
                    ))}
                  </TextField>

                  <TextField
                    label='Initial Quantity'
                    type='number'
                    value={initQuantity}
                    onChange={(event) => setInitQuantity(event.target.value)}
                    fullWidth
                    size='small'
                  />

                  <Button
                    variant='contained'
                    disabled={submittingInit}
                    onClick={() => void handleInitInventory()}
                  >
                    {submittingInit ? 'Submitting...' : 'Initialize'}
                  </Button>
                </Stack>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Typography variant='body2' sx={{ fontWeight: 600, mb: 1 }}>
                  Adjust Inventory (+/-)
                </Typography>

                <Stack spacing={1.5}>
                  <TextField
                    select
                    label='Product'
                    value={adjustProductId}
                    onChange={(event) => setAdjustProductId(event.target.value)}
                    fullWidth
                    size='small'
                  >
                    {products.map((product) => (
                      <MenuItem key={product.id} value={String(product.id)}>
                        {product.name}
                      </MenuItem>
                    ))}
                  </TextField>

                  <TextField
                    label='Change Quantity'
                    type='number'
                    value={adjustQuantity}
                    onChange={(event) => setAdjustQuantity(event.target.value)}
                    fullWidth
                    size='small'
                    helperText='Use positive for increase, negative for decrease.'
                  />

                  <Button
                    variant='contained'
                    disabled={submittingAdjust}
                    onClick={() => void handleAdjustInventory()}
                  >
                    {submittingAdjust ? 'Submitting...' : 'Adjust'}
                  </Button>
                </Stack>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Inventory Lookup
            </Typography>

            <Stack spacing={1.5}>
              <TextField
                select
                label='Product'
                value={lookupProductId}
                onChange={(event) => setLookupProductId(event.target.value)}
                fullWidth
                size='small'
              >
                {products.map((product) => (
                  <MenuItem key={product.id} value={String(product.id)}>
                    {product.name}
                  </MenuItem>
                ))}
              </TextField>

              <Button
                variant='outlined'
                onClick={() => void handleLookupInventory()}
                disabled={lookingUp}
              >
                {lookingUp ? 'Checking...' : 'Check Inventory'}
              </Button>

              {lookupResult && (
                <Paper
                  elevation={0}
                  sx={{ p: 2, borderRadius: 2, backgroundColor: '#fafafa' }}
                >
                  <Typography variant='body2' sx={{ color: '#666666' }}>
                    Product
                  </Typography>
                  <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                    {productNameById.get(lookupResult.product_id) ??
                      `Product #${lookupResult.product_id}`}
                  </Typography>
                  <Typography variant='body2' sx={{ color: '#666666' }}>
                    Quantity on hand
                  </Typography>
                  <Typography variant='h6' sx={{ fontWeight: 700 }}>
                    {lookupResult.quantity_on_hand}
                  </Typography>
                </Paper>
              )}
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Stack
              direction='row'
              justifyContent='space-between'
              alignItems='center'
              sx={{ mb: 2 }}
            >
              <Typography variant='h6' sx={{ fontWeight: 700 }}>
                Current Inventory
              </Typography>
              <Button variant='outlined' onClick={() => void loadInventory()}>
                Refresh
              </Button>
            </Stack>

            {loadingInventory ? (
              <Stack direction='row' justifyContent='center' sx={{ py: 4 }}>
                <CircularProgress size={24} />
              </Stack>
            ) : (
              <TableContainer>
                <Table size='small'>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Product</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>SKU</TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        Quantity on Hand
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {inventoryItems.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={3} sx={{ color: '#888888' }}>
                          No inventory data found.
                        </TableCell>
                      </TableRow>
                    ) : (
                      inventoryItems.map((item) => {
                        const product = productById.get(item.product_id)

                        return (
                          <TableRow key={item.product_id} hover>
                            <TableCell>
                              {product?.name ?? `Product #${item.product_id}`}
                            </TableCell>
                            <TableCell>{product?.sku ?? '-'}</TableCell>
                            <TableCell align='right'>
                              {item.quantity_on_hand}
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Inventory Logs
            </Typography>

            <Grid container spacing={1.5} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  select
                  fullWidth
                  size='small'
                  label='Filter by Product'
                  value={logProductFilter}
                  onChange={(event) => setLogProductFilter(event.target.value)}
                >
                  <MenuItem value=''>All products</MenuItem>
                  {products.map((product) => (
                    <MenuItem key={product.id} value={String(product.id)}>
                      {product.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  select
                  fullWidth
                  size='small'
                  label='Filter by Log Type'
                  value={logTypeFilter}
                  onChange={(event) => setLogTypeFilter(event.target.value)}
                >
                  <MenuItem value=''>All types</MenuItem>
                  {LOG_TYPE_OPTIONS.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <TextField
                  fullWidth
                  size='small'
                  type='number'
                  label='Limit'
                  value={logLimit}
                  onChange={(event) => setLogLimit(event.target.value)}
                />
              </Grid>

              <Grid size={{ xs: 12, md: 3 }}>
                <Stack direction='row' spacing={1}>
                  <Button
                    variant='contained'
                    fullWidth
                    onClick={() => void handleApplyLogFilters()}
                  >
                    Apply
                  </Button>
                  <Button
                    variant='outlined'
                    fullWidth
                    onClick={() => {
                      setLogProductFilter('')
                      setLogTypeFilter('')
                      setLogLimit('100')
                    }}
                  >
                    Reset
                  </Button>
                </Stack>
              </Grid>
            </Grid>

            {loadingLogs ? (
              <Stack direction='row' justifyContent='center' sx={{ py: 4 }}>
                <CircularProgress size={24} />
              </Stack>
            ) : (
              <TableContainer>
                <Table size='small'>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Date</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Product</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Type</TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        Change
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        Before
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        After
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        Ref ID
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {inventoryLogs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} sx={{ color: '#888888' }}>
                          No inventory logs found.
                        </TableCell>
                      </TableRow>
                    ) : (
                      inventoryLogs.map((log) => (
                        <TableRow key={log.id} hover>
                          <TableCell>
                            {new Date(log.log_date).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            {productNameById.get(log.product_id) ??
                              `Product #${log.product_id}`}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={log.log_type}
                              size='small'
                              sx={{
                                fontWeight: 600,
                                backgroundColor: '#f5f5f5',
                                color: '#000000',
                              }}
                            />
                          </TableCell>
                          <TableCell
                            align='right'
                            sx={{
                              color:
                                log.change_quantity > 0 ? '#2e7d32' : '#c62828',
                              fontWeight: 600,
                            }}
                          >
                            {log.change_quantity > 0
                              ? `+${log.change_quantity}`
                              : log.change_quantity}
                          </TableCell>
                          <TableCell align='right'>
                            {log.quantity_before}
                          </TableCell>
                          <TableCell align='right'>
                            {log.quantity_after}
                          </TableCell>
                          <TableCell align='right'>
                            {log.reference_id ?? '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Inventory
