import type { RouteObject } from 'react-router-dom'

import ProtectedRoute from '../components/ProtectedRoute'
import DashboardLayout from '../layouts/DashboardLayout'
import ChangePassword from '../pages/ChangePassword'
import Dashboard from '../pages/Dashboard'
import Sales from '../pages/Sales'
import Inventory from '../pages/Inventory'
import Products from '../pages/Products'

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
