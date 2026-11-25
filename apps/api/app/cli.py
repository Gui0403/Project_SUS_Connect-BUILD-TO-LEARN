"""Comandos de linha: `python -m app.cli create-admin`.

`create_user` também é usada pelos testes para criar contas sem passar pela API.
"""

import argparse
import sys
import uuid

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password


def create_user(
    email: str,
    password: str,
    role: str,
    doctor_id=None,
    full_name: str | None = None,
    must_change_password: bool = False,
) -> str:
    role_value = Role(role).value
    with SessionLocal() as db:
        user = User(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            full_name=full_name or f"System {role_value.title()}",
            role=role_value,
            doctor_id=uuid.UUID(str(doctor_id)) if doctor_id else None,
            must_change_password=must_change_password,
        )
        db.add(user)
        db.commit()
        return str(user.id)


def create_admin() -> int:
    email, password = settings.first_admin_email, settings.first_admin_password
    if not email or not password:
        print(
            "Defina FIRST_ADMIN_EMAIL e FIRST_ADMIN_PASSWORD no .env", file=sys.stderr
        )
        return 1
    if len(password) < 10:
        print(
            "FIRST_ADMIN_PASSWORD precisa ter pelo menos 10 caracteres", file=sys.stderr
        )
        return 1
    with SessionLocal() as db:
        if (
            db.scalar(select(User.id).where(User.email == email.strip().lower()))
            is not None
        ):
            print(f"Já existe um usuário com o e-mail {email}. Nada a fazer.")
            return 0
    create_user(
        email, password, "ADMIN", full_name="Administrador", must_change_password=True
    )
    print(f"ADMIN criado: {email} (troca de senha obrigatória no primeiro acesso)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=["create-admin"])
    args = parser.parse_args()
    if args.command == "create-admin":
        return create_admin()
    return 1


if __name__ == "__main__":
    sys.exit(main())
