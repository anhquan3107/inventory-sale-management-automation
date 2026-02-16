from pydantic import BaseModel


class AdminResetPasswordRequest(BaseModel):
    new_password: str