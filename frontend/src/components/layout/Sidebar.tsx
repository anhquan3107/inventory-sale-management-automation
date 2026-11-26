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
  useMediaQuery,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  ShoppingCart as SalesIcon,
  Category as CategoryIcon,
  Inventory as InventoryIcon,
  EventRepeatOutlined,
  FactCheckOutlined,
} from '@mui/icons-material'
import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'
import { useAuth } from '../../hooks/use-auth'

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'Sales', path: '/sales', icon: <SalesIcon /> },
  { label: 'Products', path: '/products', icon: <CategoryIcon /> },
  { label: 'Inventory', path: '/inventory', icon: <InventoryIcon /> },
  { label: 'Decisions', path: '/decisions', icon: <FactCheckOutlined />, adminOnly: true },
  { label: 'Replenishment', path: '/replenishment', icon: <EventRepeatOutlined />, adminOnly: true },
]

interface Props {
  mobileOpen: boolean
  onClose: () => void
}

const Sidebar = ({ mobileOpen, onClose }: Props) => {
  const location = useLocation()
  const { user } = useAuth()
  const theme = useTheme()
  const mobile = useMediaQuery(theme.breakpoints.down('md'))

  return (
    <Drawer
      variant={mobile ? 'temporary' : 'permanent'}
      open={!mobile || mobileOpen}
      onClose={onClose}
      sx={{
        width: 'var(--ims-sidebar-width, 240px)',
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 'var(--ims-sidebar-width, 240px)',
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

      <List component='nav' aria-label='Main navigation' sx={{ px: 1, pt: 1 }}>
        {navItems.filter((item) => !item.adminOnly || user?.role === 'admin').map((item) => {
          const isActive = location.pathname === item.path

          return (
            <ListItemButton
              key={item.path}
              component={Link}
              to={item.path}
              onClick={onClose}
              aria-current={isActive ? 'page' : undefined}
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
