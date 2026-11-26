"""exams

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exams",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False
        ),
        sa.Column(
            "appointment_id", sa.Uuid(), sa.ForeignKey("appointments.id"), nullable=True
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("performed_at", sa.Date(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("storage_key", name="uq_exams_storage_key"),
    )
    op.create_index("ix_exams_patient_id", "exams", ["patient_id"])


def downgrade() -> None:
    op.drop_table("exams")
