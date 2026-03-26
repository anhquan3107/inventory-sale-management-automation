import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
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
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { salesApi } from '../api/sales'
import { productsApi } from '../api/products'
import type { ProductResponse } from '../types/product'
import type {
  CreateSaleItemRequest,
  CreateSaleResponse,
  SaleDetailRead,
  SaleRead,
} from '../types/sales'

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

const Sales = () => {
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [sales, setSales] = useState<SaleRead[]>([])

  const [loadingSales, setLoadingSales] = useState(false)
  const [creatingSale, setCreatingSale] = useState(false)
  const [lookupLoading, setLookupLoading] = useState(false)

  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [salesChannel, setSalesChannel] = useState('OFFLINE')
  const [itemProductId, setItemProductId] = useState('')
  const [itemQuantity, setItemQuantity] = useState('1')
  const [itemUnitPrice, setItemUnitPrice] = useState('')
  const [saleItems, setSaleItems] = useState<CreateSaleItemRequest[]>([])

  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')
  const [filterChannel, setFilterChannel] = useState('')
  const [filterProductId, setFilterProductId] = useState('')

  const [lookupOrderId, setLookupOrderId] = useState('')
  const [lookupDetail, setLookupDetail] = useState<SaleDetailRead | null>(null)

  const productById = useMemo(() => {
    const map = new Map<number, ProductResponse>()
    products.forEach((product) => {
      map.set(product.id, product)
    })
    return map
  }, [products])

  const resetMessages = (): void => {
    setErrorMessage('')
    setSuccessMessage('')
  }

  const loadSales = async (): Promise<void> => {
    setLoadingSales(true)
    try {
      const params = {
        date_from: filterDateFrom ? `${filterDateFrom}T00:00:00` : undefined,
        date_to: filterDateTo ? `${filterDateTo}T23:59:59` : undefined,
        sales_channel: filterChannel || undefined,
        product_id: filterProductId ? Number(filterProductId) : undefined,
      }
      const data = await salesApi.list(params)
      setSales(data)
    } finally {
      setLoadingSales(false)
    }
  }

  useEffect(() => {
    const initialize = async () => {
      resetMessages()
      try {
        const [productsData, salesData] = await Promise.all([
          productsApi.list(),
          salesApi.list({}),
        ])

        setProducts(productsData)
        setSales(salesData)
      } catch (error) {
        setErrorMessage(toErrorMessage(error))
      }
    }

    void initialize()
  }, [])

  const handleProductSelectForItem = (productIdValue: string): void => {
    setItemProductId(productIdValue)
    const product = productById.get(Number(productIdValue))
    if (product) {
      setItemUnitPrice(product.unit_price)
    }
  }

  const handleAddItem = (): void => {
    resetMessages()

    const productId = Number(itemProductId)
    const quantity = Number(itemQuantity)
    const unitPrice = Number(itemUnitPrice)

    if (!itemProductId || Number.isNaN(productId)) {
      setErrorMessage('Please select a product for sale item.')
      return
    }

    if (Number.isNaN(quantity) || quantity <= 0) {
      setErrorMessage('Quantity must be greater than 0.')
      return
    }

    if (Number.isNaN(unitPrice) || unitPrice < 0) {
      setErrorMessage('Unit price must be a number greater than or equal to 0.')
      return
    }

    setSaleItems((previous) => [
      ...previous,
      {
        product_id: productId,
        quantity,
        unit_price: unitPrice,
      },
    ])

    setItemProductId('')
    setItemQuantity('1')
    setItemUnitPrice('')
  }

  const handleRemoveItem = (index: number): void => {
    setSaleItems((previous) =>
      previous.filter((_, itemIndex) => itemIndex !== index),
    )
  }

  const handleCreateSale = async (): Promise<void> => {
    resetMessages()

    if (!salesChannel.trim()) {
      setErrorMessage('Sales channel is required.')
      return
    }

    if (saleItems.length === 0) {
      setErrorMessage('Please add at least one sale item.')
      return
    }

    setCreatingSale(true)

    try {
      const response: CreateSaleResponse = await salesApi.create({
        sales_channel: salesChannel.trim().toUpperCase(),
        items: saleItems,
      })

      setSuccessMessage(
        `Sale created successfully. Order #${response.order_id}, total ${response.total_amount}.`,
      )
      setSaleItems([])
      await loadSales()
      const detail = await salesApi.getById(response.order_id)
      setLookupOrderId(String(response.order_id))
      setLookupDetail(detail)
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setCreatingSale(false)
    }
  }

  const handleApplyFilters = async (): Promise<void> => {
    resetMessages()
    try {
      await loadSales()
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    }
  }

  const handleResetFilters = (): void => {
    setFilterDateFrom('')
    setFilterDateTo('')
    setFilterChannel('')
    setFilterProductId('')
  }

  const handleLookupSale = async (): Promise<void> => {
    resetMessages()

    const orderId = Number(lookupOrderId)

    if (!lookupOrderId || Number.isNaN(orderId)) {
      setErrorMessage('Please enter a valid order ID.')
      return
    }

    setLookupLoading(true)

    try {
      const detail = await salesApi.getById(orderId)
      setLookupDetail(detail)
    } catch (error) {
      setLookupDetail(null)
      setErrorMessage(toErrorMessage(error))
    } finally {
      setLookupLoading(false)
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
              Sales
            </Typography>
            <Typography variant='body2' sx={{ color: '#666666' }}>
              Create orders, track transactions, and review sale history.
            </Typography>
          </Box>

          <Stack direction='row' spacing={1}>
            <Chip label={`Orders: ${sales.length}`} size='small' />
            <Chip label={`Draft Items: ${saleItems.length}`} size='small' />
          </Stack>
        </Stack>
      </Paper>

      <Stack spacing={2} sx={{ mb: 3 }}>
        {errorMessage && <Alert severity='error'>{errorMessage}</Alert>}
        {successMessage && <Alert severity='success'>{successMessage}</Alert>}
      </Stack>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Create Sale
            </Typography>

            <Grid container spacing={1.5} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label='Sales Channel'
                  value={salesChannel}
                  onChange={(event) => setSalesChannel(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  select
                  label='Product'
                  value={itemProductId}
                  onChange={(event) =>
                    handleProductSelectForItem(event.target.value)
                  }
                  fullWidth
                  size='small'
                >
                  <MenuItem value=''>Select product</MenuItem>
                  {products.map((product) => (
                    <MenuItem key={product.id} value={String(product.id)}>
                      {product.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <TextField
                  label='Quantity'
                  type='number'
                  value={itemQuantity}
                  onChange={(event) => setItemQuantity(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <TextField
                  label='Unit Price'
                  type='number'
                  value={itemUnitPrice}
                  onChange={(event) => setItemUnitPrice(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 1 }}>
                <Button
                  variant='outlined'
                  fullWidth
                  onClick={handleAddItem}
                  sx={{ height: '100%' }}
                >
                  Add
                </Button>
              </Grid>
            </Grid>

            <TableContainer sx={{ mb: 2 }}>
              <Table size='small'>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Product</TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align='right'>
                      Qty
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align='right'>
                      Unit Price
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align='right'>
                      Line Total
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }} align='center'>
                      Action
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {saleItems.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} sx={{ color: '#888888' }}>
                        No items added.
                      </TableCell>
                    </TableRow>
                  ) : (
                    saleItems.map((item, index) => (
                      <TableRow key={`${item.product_id}-${index}`} hover>
                        <TableCell>
                          {productById.get(item.product_id)?.name ??
                            `Product #${item.product_id}`}
                        </TableCell>
                        <TableCell align='right'>{item.quantity}</TableCell>
                        <TableCell align='right'>{item.unit_price}</TableCell>
                        <TableCell align='right'>
                          {(item.quantity * item.unit_price).toFixed(2)}
                        </TableCell>
                        <TableCell align='center'>
                          <IconButton
                            size='small'
                            onClick={() => handleRemoveItem(index)}
                          >
                            <DeleteOutlineIcon fontSize='small' />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            <Stack direction='row' justifyContent='flex-end'>
              <Button
                variant='contained'
                disabled={creatingSale}
                onClick={() => void handleCreateSale()}
              >
                {creatingSale ? 'Submitting...' : 'Create Sale'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Sale Detail Lookup
            </Typography>

            <Stack direction='row' spacing={1.5} sx={{ mb: 2 }}>
              <TextField
                label='Order ID'
                type='number'
                value={lookupOrderId}
                onChange={(event) => setLookupOrderId(event.target.value)}
                fullWidth
                size='small'
              />
              <Button
                variant='outlined'
                onClick={() => void handleLookupSale()}
                disabled={lookupLoading}
              >
                {lookupLoading ? 'Checking...' : 'Lookup'}
              </Button>
            </Stack>

            {lookupDetail && (
              <Paper
                elevation={0}
                sx={{ p: 2, borderRadius: 2, backgroundColor: '#fafafa' }}
              >
                <Typography variant='body2' sx={{ color: '#666666' }}>
                  Order ID
                </Typography>
                <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                  {lookupDetail.id}
                </Typography>

                <Typography variant='body2' sx={{ color: '#666666' }}>
                  Order Date
                </Typography>
                <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                  {new Date(lookupDetail.order_date).toLocaleString()}
                </Typography>

                <Typography variant='body2' sx={{ color: '#666666' }}>
                  Sales Channel
                </Typography>
                <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                  {lookupDetail.sales_channel}
                </Typography>

                <Typography variant='body2' sx={{ color: '#666666' }}>
                  Total Amount
                </Typography>
                <Typography variant='body1' sx={{ fontWeight: 700 }}>
                  {lookupDetail.total_amount}
                </Typography>

                <Typography
                  variant='subtitle2'
                  sx={{ mt: 2, mb: 1, fontWeight: 700 }}
                >
                  Order Items
                </Typography>

                <TableContainer>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell>Product</TableCell>
                        <TableCell align='right'>Qty</TableCell>
                        <TableCell align='right'>Unit Price</TableCell>
                        <TableCell align='right'>Line Total</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {lookupDetail.items.map((item, index) => (
                        <TableRow key={`${item.product_id}-${index}`}>
                          <TableCell>
                            {productById.get(item.product_id)?.name ??
                              `Product #${item.product_id}`}
                          </TableCell>
                          <TableCell align='right'>{item.quantity}</TableCell>
                          <TableCell align='right'>{item.unit_price}</TableCell>
                          <TableCell align='right'>{item.line_total}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Sales List
            </Typography>

            <Grid container spacing={1.5} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, md: 2.5 }}>
                <TextField
                  label='Date From'
                  type='date'
                  value={filterDateFrom}
                  onChange={(event) => setFilterDateFrom(event.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 2.5 }}>
                <TextField
                  label='Date To'
                  type='date'
                  value={filterDateTo}
                  onChange={(event) => setFilterDateTo(event.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label='Sales Channel'
                  value={filterChannel}
                  onChange={(event) => setFilterChannel(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <TextField
                  select
                  label='Product'
                  value={filterProductId}
                  onChange={(event) => setFilterProductId(event.target.value)}
                  fullWidth
                  size='small'
                >
                  <MenuItem value=''>All products</MenuItem>
                  {products.map((product) => (
                    <MenuItem key={product.id} value={String(product.id)}>
                      {product.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <Stack direction='row' spacing={1}>
                  <Button
                    variant='contained'
                    fullWidth
                    onClick={() => void handleApplyFilters()}
                  >
                    Apply
                  </Button>
                  <Button
                    variant='outlined'
                    fullWidth
                    onClick={handleResetFilters}
                  >
                    Reset
                  </Button>
                </Stack>
              </Grid>
            </Grid>

            {loadingSales ? (
              <Stack direction='row' justifyContent='center' sx={{ py: 4 }}>
                <CircularProgress size={24} />
              </Stack>
            ) : (
              <TableContainer>
                <Table size='small'>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Order ID</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Order Date</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Channel</TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        Total Amount
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sales.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} sx={{ color: '#888888' }}>
                          No sales found.
                        </TableCell>
                      </TableRow>
                    ) : (
                      sales.map((sale) => (
                        <TableRow key={sale.id} hover>
                          <TableCell>{sale.id}</TableCell>
                          <TableCell>
                            {new Date(sale.order_date).toLocaleString()}
                          </TableCell>
                          <TableCell>{sale.sales_channel}</TableCell>
                          <TableCell align='right'>
                            {sale.total_amount}
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

export default Sales
