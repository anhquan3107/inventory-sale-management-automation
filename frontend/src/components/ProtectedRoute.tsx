// src/components/ProtectedRoute.tsx

import { Navigate, Outlet } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
import { useAuth } from '../hooks/use-auth'

const ProtectedRoute = () => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <Box
        display='flex'
        justifyContent='center'
        alignItems='center'
        height='100vh'
      >
        <CircularProgress />
      </Box>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to='/login' replace />
  }

  return <Outlet />
}

export default ProtectedRoute
