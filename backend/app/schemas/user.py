import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

USER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{3,50}$")

class UserCreate(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=50, description="Unique login user ID")
    password: str = Field(..., min_length=8, max_length=128, description="Initial account password (min 8 chars)")
    display_name: str = Field(..., min_length=2, max_length=100, description="Full name or badge/callsign")
    role: str = Field(default="investigator", description="Role: 'admin' or 'investigator'")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not USER_ID_REGEX.match(cleaned):
            raise ValueError("user_id must be 3-50 characters and contain only letters, numbers, hyphens, dots, or underscores.")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role = v.strip().lower()
        if role not in ("admin", "investigator"):
            raise ValueError("Role must be either 'admin' or 'investigator'.")
        return role

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        role = v.strip().lower()
        if role not in ("admin", "investigator"):
            raise ValueError("Role must be either 'admin' or 'investigator'.")
        return role

class UserResponse(BaseModel):
    user_id: str
    display_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None
    created_by: Optional[str] = None
