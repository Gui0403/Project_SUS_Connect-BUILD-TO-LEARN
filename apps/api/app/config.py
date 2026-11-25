"""Configuração lida das variáveis de ambiente (12 Factor)."""

import os
from dataclasses import dataclass


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Váriavel de ambiente {name} não definida. "
            "Copie as variáveis de auth do env.example para o seu .env."
        )
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    max_failed_logins: int
    lockout_minutes: int
    first_admin_email: str | None
    first_admin_password: str | None


settings = Settings(
    database_url=_required("DATABASE_URL"),
    jwt_secret=_required("JWT_SECRET"),
    jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(
        os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    ),
    refresh_token_expire_days=int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    max_failed_logins=5,
    lockout_minutes=15,
    first_admin_email=os.environ.get("FIRST_ADMIN_EMAIL"),
    first_admin_password=os.environ.get("FIRST_ADMIN_PASSWORD"),
)
