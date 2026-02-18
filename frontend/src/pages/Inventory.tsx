import { Box, Typography, Paper } from '@mui/material'

const Inventory = () => {
  return (
    <Box>
      <Typography variant='h5' sx={{ fontWeight: 700, mb: 3 }}>
        Inventory
      </Typography>

      <Paper
        elevation={0}
        sx={{
          p: 4,
          border: '1px solid #e0e0e0',
          borderRadius: 2,
          textAlign: 'center',
          color: '#888888',
        }}
      >
        <Typography variant='body1'>
          Inventory management coming soon.
        </Typography>
      </Paper>
    </Box>
  )
}

export default Inventory
