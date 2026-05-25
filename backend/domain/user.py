from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
        }


@dataclass
class RefreshToken:
    id: int
    user_id: int
    token: str
    expires_at: datetime
    created_at: Optional[datetime] = None
    revoked: bool = False


@dataclass
class BlacklistedToken:
    id: int
    jti: str
    expires_at: datetime
    created_at: Optional[datetime] = None
