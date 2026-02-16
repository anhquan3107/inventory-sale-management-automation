import type { RouteObject } from 'react-router-dom'

import ProtectedRoute from '../components/ProtectedRoute'

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
]
