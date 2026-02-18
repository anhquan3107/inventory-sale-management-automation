import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material'
import { Logout as LogoutIcon } from '@mui/icons-material'
import { useAuth } from '../../hooks/use-auth'
import { useNavigate } from 'react-router-dom'

const DRAWER_WIDTH = 240

const TopBar = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <AppBar
      position='fixed'
      elevation={0}
      sx={{
        width: `calc(100% - ${DRAWER_WIDTH}px)`,
        ml: `${DRAWER_WIDTH}px`,
        backgroundColor: '#ffffff',
        color: '#000000',
        borderBottom: '1px solid #e0e0e0',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Typography variant='h6' sx={{ fontWeight: 600, fontSize: '1rem' }}>
          Inventory Management
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography
            variant='body2'
            sx={{ color: '#666666', fontWeight: 500 }}
          >
            {user?.username}
          </Typography>

          <Button
            size='small'
            variant='outlined'
            onClick={handleLogout}
            startIcon={<LogoutIcon />}
            sx={{
              color: '#000000',
              borderColor: '#e0e0e0',
              textTransform: 'none',
              fontWeight: 500,
              '&:hover': {
                borderColor: '#000000',
                backgroundColor: '#f5f5f5',
              },
            }}
          >
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  )
}

export default TopBar
