import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import {
  Inventory as InventoryIcon,
  ShoppingCart as SalesIcon,
  TrendingUp as TrendingIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'
import { dashboardApi } from '../api/dashboard'
import type {
  DashboardSummaryResponse,
  LowStockItem,
  RecentSaleItem,
  RevenueTrendItem,
  TopProductItem,
} from '../types/dashboard'

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

const formatCurrency = (value: string | number): string => {
  const numeric = Number(value)

  if (Number.isNaN(numeric)) {
    return String(value)
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(numeric)
}

const Dashboard = () => {
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null)
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendItem[]>([])
  const [topProducts, setTopProducts] = useState<TopProductItem[]>([])
  const [lowStockItems, setLowStockItems] = useState<LowStockItem[]>([])
  const [recentSales, setRecentSales] = useState<RecentSaleItem[]>([])

  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const summaryCards = useMemo(
    () => [
      {
        title: 'Revenue Today',
        value: formatCurrency(summary?.revenue_today ?? 0),
        icon: <TrendingIcon />,
      },
      {
        title: 'Revenue This Month',
        value: formatCurrency(summary?.revenue_month ?? 0),
        icon: <InventoryIcon />,
      },
      {
        title: 'Orders Today',
        value: String(summary?.orders_today ?? 0),
        icon: <SalesIcon />,
      },
      {
        title: 'Low Stock Items',
        value: String(summary?.low_stock_count ?? 0),
        icon: <WarningIcon />,
      },
    ],
    [summary],
  )

  const loadDashboard = async (): Promise<void> => {
    setLoading(true)
    setErrorMessage('')

    try {
      const [
        summaryData,
        revenueTrendData,
        topProductsData,
        lowStockData,
        recentSalesData,
      ] = await Promise.all([
        dashboardApi.getSummary(),
        dashboardApi.getRevenueTrend(7),
        dashboardApi.getTopProducts(5),
        dashboardApi.getLowStock(),
        dashboardApi.getRecentSales(5),
      ])

      setSummary(summaryData)
      setRevenueTrend(revenueTrendData)
      setTopProducts(topProductsData)
      setLowStockItems(lowStockData)
      setRecentSales(recentSalesData)
    } catch (error) {
      setErrorMessage(toErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDashboard()
  }, [])

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
              Dashboard
            </Typography>
            <Typography variant='body2' sx={{ color: '#666666' }}>
              Snapshot of business performance and inventory alerts.
            </Typography>
          </Box>

          <Stack direction='row' spacing={1}>
            <Chip label='Window: 7 days' size='small' />
            <Button
              variant='outlined'
              size='small'
              onClick={() => void loadDashboard()}
              disabled={loading}
            >
              Refresh
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Stack spacing={2} sx={{ mb: 3 }}>
        {errorMessage && <Alert severity='error'>{errorMessage}</Alert>}
      </Stack>

      {loading ? (
        <Paper elevation={0} sx={{ p: 4, borderRadius: 3 }}>
          <Stack direction='row' justifyContent='center' sx={{ py: 4 }}>
            <CircularProgress size={24} />
          </Stack>
        </Paper>
      ) : (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            {summaryCards.map((card) => (
              <Grid key={card.title} size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      backgroundColor: '#f5f5f5',
                      color: '#000000',
                      display: 'flex',
                    }}
                  >
                    {card.icon}
                  </Box>
                  <Box>
                    <Typography
                      variant='body2'
                      sx={{ color: '#888888', fontWeight: 500 }}
                    >
                      {card.title}
                    </Typography>
                    <Typography variant='h5' sx={{ fontWeight: 700 }}>
                      {card.value}
                    </Typography>
                  </Box>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
                <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
                  Revenue Trend (7 days)
                </Typography>

                <TableContainer>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Date</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align='right'>
                          Revenue
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {revenueTrend.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2} sx={{ color: '#888888' }}>
                            No revenue records.
                          </TableCell>
                        </TableRow>
                      ) : (
                        revenueTrend.map((item) => (
                          <TableRow key={item.date} hover>
                            <TableCell>
                              {new Date(item.date).toLocaleDateString()}
                            </TableCell>
                            <TableCell align='right'>
                              {formatCurrency(item.revenue)}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
                <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
                  Top Products
                </Typography>

                <TableContainer>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Product</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align='right'>
                          Sold Qty
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {topProducts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2} sx={{ color: '#888888' }}>
                            No product sales records.
                          </TableCell>
                        </TableRow>
                      ) : (
                        topProducts.map((item) => (
                          <TableRow key={item.product_id} hover>
                            <TableCell>{item.product_name}</TableCell>
                            <TableCell align='right'>
                              {item.total_quantity_sold}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
                <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
                  Low Stock Alerts
                </Typography>

                <TableContainer>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Product</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align='right'>
                          Current Stock
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {lowStockItems.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2} sx={{ color: '#888888' }}>
                            No low stock items.
                          </TableCell>
                        </TableRow>
                      ) : (
                        lowStockItems.map((item) => (
                          <TableRow key={item.product_id} hover>
                            <TableCell>{item.product_name}</TableCell>
                            <TableCell align='right'>{item.current_stock}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 6 }}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 3 }}>
                <Typography variant='h6' sx={{ fontWeight: 700, mb: 2 }}>
                  Recent Sales
                </Typography>

                <TableContainer>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Order</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Channel</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align='right'>
                          Amount
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {recentSales.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={3} sx={{ color: '#888888' }}>
                            No recent sales.
                          </TableCell>
                        </TableRow>
                      ) : (
                        recentSales.map((item) => (
                          <TableRow key={item.sale_id} hover>
                            <TableCell>
                              #{item.sale_id}{' '}
                              <Typography
                                component='span'
                                variant='body2'
                                sx={{ color: '#888888' }}
                              >
                                ({new Date(item.created_at).toLocaleDateString()})
                              </Typography>
                            </TableCell>
                            <TableCell>{item.sales_channel}</TableCell>
                            <TableCell align='right'>
                              {formatCurrency(item.total_amount)}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  )
}

export default Dashboard
