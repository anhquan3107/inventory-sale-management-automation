import axiosInstance from '../api/axios'
import { API_PATHS } from '../api/paths'
import type {
  LoginRequest,
  LoginResponse,
  UserResponse,
  ChangePasswordRequest,
} from '../types/auth'

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await axiosInstance.post(API_PATHS.AUTH.LOGIN, data)
    return response.data
  },

  getMe: async (): Promise<UserResponse> => {
    const response = await axiosInstance.get(API_PATHS.AUTH.ME)
    return response.data
  },

  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    await axiosInstance.put(API_PATHS.AUTH.CHANGE_PASSWORD, data)
  },
}
