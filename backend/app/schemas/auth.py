from pydantic import BaseModel


class LoginRequest(BaseModel):
    identifier: str
    password: str



class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    must_change_password: bool
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    id: int
    username: str
    role: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
