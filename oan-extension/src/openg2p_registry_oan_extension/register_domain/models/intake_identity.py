"""OAN intake identity-verification state.

The platform registrant-authentication tables are tied to an existing register
record. Farmer intake needs a separate, short-lived context because the record
does not exist until approval. Tokens never belong in these tables; only a hash
and the minimum encrypted claims needed to apply the configured mapping are
retained.
"""

import uuid
from datetime import datetime

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class OANIntakeIdentityContext(BaseORMModel):
    __tablename__ = "oan_intake_identity_contexts"

    context_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    submission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    form_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True)
    issuer: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    mapped_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    protected_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_oan_intake_identity_owner_form", "created_by", "form_id", "status"),
    )


class OANIntakeIdentityAttempt(BaseORMModel):
    __tablename__ = "oan_intake_identity_attempts"

    attempt_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    context_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True)
    issuer: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    encrypted_claims: Mapped[str | None] = mapped_column(String, nullable=True)
    authentication_method: Mapped[str | None] = mapped_column(String, nullable=True)
    claim_verifications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
