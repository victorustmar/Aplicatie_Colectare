from pydantic import BaseModel
from typing import Optional
from app.schemas.auth import LoginOut  # reutilizăm structura (token + user)

class AcceptInviteIn(BaseModel):
    token: str
    password: str
    full_name: str
