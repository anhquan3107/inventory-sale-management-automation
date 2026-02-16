import { Navigate, useRoutes } from 'react-router-dom'

import { publicRoutes } from './public-routes'
import { protectedRoutes } from './protected-routes'

export default function AppRoutes() {
  const routes = useRoutes([
    ...publicRoutes,
    ...protectedRoutes,
    // Default redirect
    {
      path: '/',
      element: <Navigate to='/dashboard' replace />,
    },
    // 404 fallback
    {
      path: '*',
      element: <Navigate to='/dashboard' replace />,
    },
  ])

  return routes
}
