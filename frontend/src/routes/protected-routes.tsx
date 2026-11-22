import { lazy, Suspense } from 'react'
import { Box, CircularProgress } from '@mui/material'
import type { RouteObject } from 'react-router-dom'

import ProtectedRoute from '../components/ProtectedRoute'
import DashboardLayout from '../layouts/DashboardLayout'
import ChangePassword from '../pages/ChangePassword'
import Dashboard from '../pages/Dashboard'
import Sales from '../pages/Sales'
import Inventory from '../pages/Inventory'
import Products from '../pages/Products'

const Replenishment = lazy(() => import('../pages/Replenishment'))

export const protectedRoutes: RouteObject[] = [
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          { path: '/dashboard', element: <Dashboard /> },
          { path: '/sales', element: <Sales /> },
          { path: '/products', element: <Products /> },
          { path: '/inventory', element: <Inventory /> },
          {
            path: '/replenishment',
            element: (
              <Suspense fallback={<Box role='status' aria-label='Loading replenishment' sx={{ display: 'grid', placeItems: 'center', py: 6 }}><CircularProgress /></Box>}>
                <Replenishment />
              </Suspense>
            ),
          },
        ],
      },
      {
        // Change password outside layout (full-screen, like login)
        path: '/change-password',
        element: <ChangePassword />,
      },
    ],
  },
]
