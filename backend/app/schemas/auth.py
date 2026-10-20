from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse

class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class BootstrapRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(default="Primary System Administrator", min_length=2, max_length=100)
    bootstrap_key: Optional[str] = None
