import type { RouteObject } from 'react-router-dom'

import ProtectedRoute from '../components/ProtectedRoute'
import ChangePassword from '../pages/ChangePassword'

// Placeholder - move to pages/ when implementing
const Dashboard = () => {
  return <div>Dashboard Page</div>
}

export const protectedRoutes: RouteObject[] = [
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },
  {
    path: '/change-password',
    element: (
      <ProtectedRoute>
        <ChangePassword />
      </ProtectedRoute>
    ),
  },
]
