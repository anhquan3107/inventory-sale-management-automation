import { useEffect, useState } from 'react'
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
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { productsApi } from '../api/products'
import type {
  CreateProductRequest,
  ProductResponse,
  UpdateProductRequest,
} from '../types/product'

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

const Products = () => {
  const [products, setProducts] = useState<ProductResponse[]>([])
  const [loadingProducts, setLoadingProducts] = useState(false)

  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [sku, setSku] = useState('')
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [unitPrice, setUnitPrice] = useState('')
  const [submittingCreate, setSubmittingCreate] = useState(false)

  const [lookupProductId, setLookupProductId] = useState('')
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupResult, setLookupResult] = useState<ProductResponse | null>(null)

  const [updateProductId, setUpdateProductId] = useState('')
  const [updateName, setUpdateName] = useState('')
  const [updateCategory, setUpdateCategory] = useState('')
  const [updateUnitPrice, setUpdateUnitPrice] = useState('')
  const [updateIsActive, setUpdateIsActive] = useState(true)
  const [submittingUpdate, setSubmittingUpdate] = useState(false)

  const loadProducts = async (): Promise<void> => {
    setLoadingProducts(true)

    try {
      const data = await productsApi.list()
      setProducts(data)
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setLoadingProducts(false)
    }
  }

  useEffect(() => {
    void loadProducts()
  }, [])

  const resetMessages = (): void => {
    setErrorMessage('')
    setSuccessMessage('')
  }

  const handleCreateProduct = async (): Promise<void> => {
    resetMessages()

    const parsedUnitPrice = Number(unitPrice)

    if (!sku.trim()) {
      setErrorMessage('SKU is required.')
      return
    }

    if (!name.trim()) {
      setErrorMessage('Name is required.')
      return
    }

    if (Number.isNaN(parsedUnitPrice) || parsedUnitPrice < 0) {
      setErrorMessage('Unit price must be a number greater than or equal to 0.')
      return
    }

    const payload: CreateProductRequest = {
      sku: sku.trim(),
      name: name.trim(),
      category: category.trim() ? category.trim() : null,
      unit_price: parsedUnitPrice,
    }

    setSubmittingCreate(true)

    try {
      await productsApi.create(payload)
      setSuccessMessage('Product initialized successfully.')
      setSku('')
      setName('')
      setCategory('')
      setUnitPrice('')
      await loadProducts()
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setSubmittingCreate(false)
    }
  }

  const handleLookupProduct = async (): Promise<void> => {
    resetMessages()

    const productId = Number(lookupProductId)

    if (!lookupProductId || Number.isNaN(productId)) {
      setErrorMessage('Please select a product for detail lookup.')
      return
    }

    setLookupLoading(true)

    try {
      const data = await productsApi.getById(productId)
      setLookupResult(data)
    } catch (error) {
      setLookupResult(null)
      setErrorMessage(toErrorMessage(error))
    } finally {
      setLookupLoading(false)
    }
  }

  const handleUpdateProduct = async (): Promise<void> => {
    resetMessages()

    const productId = Number(updateProductId)

    if (!updateProductId || Number.isNaN(productId)) {
      setErrorMessage('Please select a product to update.')
      return
    }

    const payload: UpdateProductRequest = {
      is_active: updateIsActive,
    }

    if (updateName.trim()) {
      payload.name = updateName.trim()
    }

    if (updateCategory.trim()) {
      payload.category = updateCategory.trim()
    }

    if (updateUnitPrice.trim()) {
      const parsedUnitPrice = Number(updateUnitPrice)
      if (Number.isNaN(parsedUnitPrice) || parsedUnitPrice < 0) {
        setErrorMessage(
          'Update unit price must be a number greater than or equal to 0.',
        )
        return
      }
      payload.unit_price = parsedUnitPrice
    }

    setSubmittingUpdate(true)

    try {
      await productsApi.update(productId, payload)
      setSuccessMessage('Product updated successfully.')
      setUpdateName('')
      setUpdateCategory('')
      setUpdateUnitPrice('')
      await loadProducts()
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setSubmittingUpdate(false)
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
              Products
            </Typography>
            <Typography variant='body2' sx={{ color: '#666666' }}>
              Manage product catalog, details, and activation status.
            </Typography>
          </Box>

          <Chip label={`Total Products: ${products.length}`} size='small' />
        </Stack>
      </Paper>

      <Stack spacing={2} sx={{ mb: 3 }}>
        {errorMessage && <Alert severity='error'>{errorMessage}</Alert>}
        {successMessage && <Alert severity='success'>{successMessage}</Alert>}
      </Stack>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Initialize Product
            </Typography>

            <Stack spacing={1.5}>
              <TextField
                label='SKU'
                value={sku}
                onChange={(event) => setSku(event.target.value)}
                fullWidth
                size='small'
              />
              <TextField
                label='Name'
                value={name}
                onChange={(event) => setName(event.target.value)}
                fullWidth
                size='small'
              />
              <TextField
                label='Category (optional)'
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                fullWidth
                size='small'
              />
              <TextField
                label='Unit Price'
                type='number'
                value={unitPrice}
                onChange={(event) => setUnitPrice(event.target.value)}
                fullWidth
                size='small'
              />

              <Button
                variant='contained'
                disabled={submittingCreate}
                onClick={() => void handleCreateProduct()}
              >
                {submittingCreate ? 'Submitting...' : 'Initialize Product'}
              </Button>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Product Lookup
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
                <MenuItem value=''>Select product</MenuItem>
                {products.map((product) => (
                  <MenuItem key={product.id} value={String(product.id)}>
                    {product.name}
                  </MenuItem>
                ))}
              </TextField>

              <Button
                variant='outlined'
                onClick={() => void handleLookupProduct()}
                disabled={lookupLoading}
              >
                {lookupLoading ? 'Checking...' : 'Get Product Detail'}
              </Button>

              {lookupResult && (
                <Paper
                  elevation={0}
                  sx={{ p: 2, borderRadius: 2, backgroundColor: '#fafafa' }}
                >
                  <Typography variant='body2' sx={{ color: '#666666' }}>
                    SKU
                  </Typography>
                  <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                    {lookupResult.sku}
                  </Typography>

                  <Typography variant='body2' sx={{ color: '#666666' }}>
                    Name
                  </Typography>
                  <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                    {lookupResult.name}
                  </Typography>

                  <Typography variant='body2' sx={{ color: '#666666' }}>
                    Unit Price
                  </Typography>
                  <Typography variant='body1' sx={{ fontWeight: 600, mb: 1 }}>
                    {lookupResult.unit_price}
                  </Typography>

                  <Typography variant='body2' sx={{ color: '#666666' }}>
                    Active
                  </Typography>
                  <Typography variant='body1' sx={{ fontWeight: 600 }}>
                    {lookupResult.is_active ? 'Yes' : 'No'}
                  </Typography>
                </Paper>
              )}
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
            <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
              Update Product
            </Typography>

            <Grid container spacing={1.5}>
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  select
                  label='Product'
                  value={updateProductId}
                  onChange={(event) => setUpdateProductId(event.target.value)}
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

              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label='New Name'
                  value={updateName}
                  onChange={(event) => setUpdateName(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <TextField
                  label='New Category'
                  value={updateCategory}
                  onChange={(event) => setUpdateCategory(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 2 }}>
                <TextField
                  label='New Unit Price'
                  type='number'
                  value={updateUnitPrice}
                  onChange={(event) => setUpdateUnitPrice(event.target.value)}
                  fullWidth
                  size='small'
                />
              </Grid>

              <Grid size={{ xs: 12, md: 1 }}>
                <Stack
                  direction='row'
                  alignItems='center'
                  justifyContent='center'
                  sx={{ height: '100%' }}
                >
                  <Switch
                    checked={updateIsActive}
                    onChange={(_, checked) => setUpdateIsActive(checked)}
                  />
                </Stack>
              </Grid>

              <Grid size={{ xs: 12, md: 1 }}>
                <Button
                  variant='contained'
                  fullWidth
                  disabled={submittingUpdate}
                  onClick={() => void handleUpdateProduct()}
                >
                  {submittingUpdate ? '...' : 'Save'}
                </Button>
              </Grid>
            </Grid>
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
                Products List
              </Typography>
              <Button variant='outlined' onClick={() => void loadProducts()}>
                Refresh
              </Button>
            </Stack>

            {loadingProducts ? (
              <Stack direction='row' justifyContent='center' sx={{ py: 4 }}>
                <CircularProgress size={24} />
              </Stack>
            ) : (
              <TableContainer>
                <Table size='small'>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>ID</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>SKU</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Name</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Category</TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='right'>
                        Unit Price
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align='center'>
                        Active
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {products.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} sx={{ color: '#888888' }}>
                          No products found.
                        </TableCell>
                      </TableRow>
                    ) : (
                      products.map((product) => (
                        <TableRow key={product.id} hover>
                          <TableCell>{product.id}</TableCell>
                          <TableCell>{product.sku}</TableCell>
                          <TableCell>{product.name}</TableCell>
                          <TableCell>{product.category ?? '-'}</TableCell>
                          <TableCell align='right'>
                            {product.unit_price}
                          </TableCell>
                          <TableCell align='center'>
                            {product.is_active ? 'Yes' : 'No'}
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

export default Products
