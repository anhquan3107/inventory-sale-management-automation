import { Box, Typography, Paper, Grid } from '@mui/material'
import {
  Inventory as InventoryIcon,
  ShoppingCart as SalesIcon,
  TrendingUp as TrendingIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'

const summaryCards = [
  {
    title: 'Total Products',
    value: '—',
    icon: <InventoryIcon />,
  },
  {
    title: 'Total Sales',
    value: '—',
    icon: <SalesIcon />,
  },
  {
    title: 'Revenue',
    value: '—',
    icon: <TrendingIcon />,
  },
  {
    title: 'Low Stock Items',
    value: '—',
    icon: <WarningIcon />,
  },
]

const Dashboard = () => {
  return (
    <Box>
      <Typography variant='h5' sx={{ fontWeight: 700, mb: 3 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {summaryCards.map((card) => (
          <Grid key={card.title} size={{ xs: 12, sm: 6, md: 3 }}>
            <Paper
              elevation={0}
              sx={{
                p: 3,
                border: '1px solid #e0e0e0',
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
    </Box>
  )
}

export default Dashboard
