# EDM v2.1 — Auth Schemas

from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = Field(None, max_length=255)
    company_name: str = Field(..., max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict
