import { useState } from 'react'
import { Box, Toolbar } from '@mui/material'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'

const DashboardLayout = () => {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', '--ims-sidebar-width': '240px' }}>
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <Box
        sx={{
          flexGrow: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          ml: 0,
        }}
      >
        <TopBar mobileOpen={mobileOpen} onOpenMenu={() => setMobileOpen(true)} />

        {/* Offset for fixed AppBar */}
        <Toolbar />

        <Box
          component='main'
          sx={{
            flexGrow: 1,
            p: { xs: 1.5, sm: 2, md: 3 },
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
