import type { RouteObject } from 'react-router-dom'

import Login from '../pages/Login'

export const publicRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <Login />,
  },
]
