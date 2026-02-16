// src/contexts/auth-context.ts

import { createContext } from 'react'
import type { UserResponse } from '../../types/auth'

export interface AuthContextType {
  user: UserResponse | null
  isAuthenticated: boolean
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)
