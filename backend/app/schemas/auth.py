from pydantic import BaseModel
from models.enums.user_role import UserRole


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
    email: str
    role: UserRole

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
