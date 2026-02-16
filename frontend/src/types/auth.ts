export interface LoginRequest {
  identifier: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  must_change_password: boolean
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface UserResponse {
  id: number
  username: string
  email?: string
}
