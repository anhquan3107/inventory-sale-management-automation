import { AppBar, Toolbar, Typography, Button, Box, IconButton } from '@mui/material'
import { Logout as LogoutIcon, Menu as MenuIcon } from '@mui/icons-material'
import { useAuth } from '../../hooks/use-auth'
import { useNavigate } from 'react-router-dom'

interface Props {
  mobileOpen: boolean
  onOpenMenu: () => void
}

const TopBar = ({ mobileOpen, onOpenMenu }: Props) => {
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
        width: { xs: '100%', md: 'calc(100% - var(--ims-sidebar-width))' },
        backgroundColor: '#ffffff',
        color: '#000000',
        borderBottom: '1px solid #e0e0e0',
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, gap: 0.75 }}>
          <IconButton aria-label='Open navigation' aria-expanded={mobileOpen} edge='start' onClick={onOpenMenu}
            sx={{ display: { md: 'none' } }}>
            <MenuIcon />
          </IconButton>
          <Typography variant='h6' noWrap sx={{ fontWeight: 600, fontSize: '1rem' }}>
            Inventory Management
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography
            variant='body2'
            sx={{ color: '#666666', fontWeight: 500, display: { xs: 'none', sm: 'block' } }}
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
