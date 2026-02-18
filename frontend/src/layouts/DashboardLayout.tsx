import { Box, Toolbar } from '@mui/material'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'

const DashboardLayout = () => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />

      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          ml: 0,
        }}
      >
        <TopBar />

        {/* Offset for fixed AppBar */}
        <Toolbar />

        <Box
          component='main'
          sx={{
            flexGrow: 1,
            p: 3,
            backgroundColor: '#f4f6f8',
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}

export default DashboardLayout
