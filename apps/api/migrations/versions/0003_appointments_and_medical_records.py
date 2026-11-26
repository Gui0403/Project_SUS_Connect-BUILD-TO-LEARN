"""appointments and medical records

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False
        ),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("reason", sa.String(500), nullable=False),
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
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])

    op.create_table(
        "medical_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "appointment_id",
            sa.Uuid(),
            sa.ForeignKey("appointments.id"),
            nullable=False,
        ),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False
        ),
        sa.Column("anamnesis", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("cid10_code", sa.String(10), nullable=True),
        sa.Column("conduct", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("appointment_id", name="uq_medical_records_appointment"),
    )
    op.create_index("ix_medical_records_patient_id", "medical_records", ["patient_id"])

    op.create_table(
        "medical_record_addenda",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "medical_record_id",
            sa.Uuid(),
            sa.ForeignKey("medical_records.id"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_medical_record_addenda_record_id",
        "medical_record_addenda",
        ["medical_record_id"],
    )


def downgrade() -> None:
    op.drop_table("medical_record_addenda")
    op.drop_table("medical_records")
    op.drop_table("appointments")
