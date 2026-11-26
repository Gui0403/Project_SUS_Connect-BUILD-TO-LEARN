"""doctors and patients

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("license_number", sa.String(20), nullable=False),
        sa.Column("license_state", sa.String(2), nullable=False),
        sa.Column("specialty", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "license_number", "license_state", name="uq_doctors_license"
        ),
    )

    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("cpf", sa.String(11), nullable=False),
        sa.Column("cns", sa.String(15), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", postgresql.JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_patients_full_name", "patients", ["full_name"])
    op.create_index("ix_patients_cpf", "patients", ["cpf"], unique=True)

    # A coluna users.doctor_id já existia (migração 0001); agora ela passa a referenciar doctors.
    op.create_foreign_key(
        "fk_users_doctor_id", "users", "doctors", ["doctor_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_doctor_id", "users", type_="foreignkey")
    op.drop_table("patients")
    op.drop_table("doctors")
