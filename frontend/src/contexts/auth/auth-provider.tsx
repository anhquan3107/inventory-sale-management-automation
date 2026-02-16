// src/contexts/auth-provider.tsx
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { UserResponse } from '../../types/auth'

import { authApi } from '../../api/auth'
import { AuthContext } from '../auth/auth-context'

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  const isAuthenticated = Boolean(user)

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token')

      if (!token) {
        setLoading(false)
        return
      }

      try {
        const userData = await authApi.getMe()
        setUser(userData)
      } catch {
        localStorage.removeItem('access_token')
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [])

  const login = async (username: string, password: string) => {
    const response = await authApi.login({ username, password })

    localStorage.setItem('access_token', response.access_token)

    const userData = await authApi.getMe()
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
