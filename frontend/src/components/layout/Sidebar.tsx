import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Divider,
  Box,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  ShoppingCart as SalesIcon,
  Inventory as InventoryIcon,
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'

const DRAWER_WIDTH = 240

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'Sales', path: '/sales', icon: <SalesIcon /> },
  { label: 'Inventory', path: '/inventory', icon: <InventoryIcon /> },
]

const Sidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Drawer
      variant='permanent'
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: '#ffffff',
          borderRight: '1px solid #e0e0e0',
        },
      }}
    >
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          px: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <InventoryIcon sx={{ color: '#000000', fontSize: 28 }} />
          <Typography
            variant='subtitle1'
            sx={{ fontWeight: 700, color: '#000000', letterSpacing: '-0.5px' }}
          >
            IMS
          </Typography>
        </Box>
      </Toolbar>

      <Divider />

      <List sx={{ px: 1, pt: 1 }}>
        {navItems.map((item) => {
          const isActive = location.pathname === item.path

          return (
            <ListItemButton
              key={item.path}
              onClick={() => navigate(item.path)}
              selected={isActive}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                '&.Mui-selected': {
                  backgroundColor: '#000000',
                  color: '#ffffff',
                  '&:hover': {
                    backgroundColor: '#1a1a1a',
                  },
                  '& .MuiListItemIcon-root': {
                    color: '#ffffff',
                  },
                },
                '&:hover': {
                  backgroundColor: '#f0f0f0',
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 40,
                  color: isActive ? '#ffffff' : '#666666',
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: '0.875rem',
                  fontWeight: isActive ? 600 : 400,
                }}
              />
            </ListItemButton>
          )
        })}
      </List>
    </Drawer>
  )
}

export default Sidebar
