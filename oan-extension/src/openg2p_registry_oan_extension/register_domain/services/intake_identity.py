"""Farmer intake authentication orchestration.

The provider, callback origin and claim mapping are configuration data on the
existing OpenG2P authentication-provider record. This service only owns the
intake-specific lifecycle and never stores raw tokens.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from iam_core.schemas import TokenEndpointAuthMethod
from iam_core.services.auth_transaction_store import AuthTransactionStore
from iam_core.services.redis_auth_transaction_store import RedisAuthTransactionStore
from iam_core.user_auth.adapters import AdapterFactory
from openg2p_fastapi_common.context import get_async_session_maker
from openg2p_fastapi_common.crypto import CryptoFactory
from openg2p_fastapi_common.service import BaseService
from openg2p_registry_core.config import Settings as CoreSettings
from openg2p_registry_core.errors import G2PRegistryErrorCodes, G2PRegistryException
from openg2p_registry_core.models import (
    G2PIntakeFormSubmission,
    G2PIntakeFormSubmissionDocument,
    G2PRegistrantAuthenticationProvider,
)
from openg2p_registry_core.services.g2p_registrant_authentication_service import (
    G2PRegistrantAuthenticationService,
)
from sqlalchemy import select

_logger = logging.getLogger("oan-intake-identity-service")
_config = CoreSettings.get_config()
_FARMER_REGISTER_MNEMONIC = "Farmer"
_FARMER_DOCUMENT_SECTION = "bc882922-9008-4902-8f4f-98db0fa8f9ad"
_IDENTITY_DOCUMENT_LABELS = {"id_proof", "aadhaar_card", "identity_document_1"}
_MOCK_FAYDA_ISSUER = "https://mock-fayda.local"
_MOCK_FAYDA_RECORDS: dict[str, dict[str, Any]] = {
    "100000000001": {
        "first_name": "Abebe", "middle_name": "Kebede", "last_name": "Tadesse",
        "first_name_amh": "አበበ", "middle_name_amh": "ከበደ", "last_name_amh": "ታደሰ",
        "birth_date": "1988-04-12", "gender": "MALE", "foundational_id": "100000000001",
    },
    "100000000002": {
        "first_name": "Almaz", "middle_name": "Desta", "last_name": "Bekele",
        "first_name_amh": "አልማዝ", "middle_name_amh": "ደስታ", "last_name_amh": "በቀለ",
        "birth_date": "1992-09-23", "gender": "FEMALE", "foundational_id": "100000000002",
    },
    "100000000003": {
        "first_name": "Dawit", "middle_name": "Mekonnen", "last_name": "Hailu",
        "first_name_amh": "ዳዊት", "middle_name_amh": "መኮንን", "last_name_amh": "ሀይሉ",
        "birth_date": "1979-01-30", "gender": "MALE", "foundational_id": "100000000003",
    },
    "100000000004": {
        "first_name": "Hana", "middle_name": "Tesfaye", "last_name": "Girma",
        "first_name_amh": "ሀና", "middle_name_amh": "ተስፋዬ", "last_name_amh": "ግርማ",
        "birth_date": "1996-06-08", "gender": "FEMALE", "foundational_id": "100000000004",
    },
}


class _ClaimsCrypto:
    def __init__(self, key: str | None):
        self._fernet = None
        if key:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, claims: dict[str, Any]) -> str:
        raw = json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return self._fernet.encrypt(raw).decode("utf-8") if self._fernet else raw.decode("utf-8")


class OANIntakeIdentityService(BaseService):
    def __init__(self):
        super().__init__()
        self._adapters = AdapterFactory.get_component()
        self._crypto = _ClaimsCrypto(_config.registrant_auth_claims_encryption_key)
        backend = (_config.registrant_auth_session_store_backend or "memory").strip().lower()
        ttl = int(_config.registrant_auth_session_ttl_seconds or 300)
        if backend == "redis" and _config.registrant_auth_redis_url:
            self._auth_tx_store = RedisAuthTransactionStore(
                ttl_seconds=ttl, redis_url=_config.registrant_auth_redis_url
            )
        else:
            self._auth_tx_store = AuthTransactionStore(ttl_seconds=ttl)

    @staticmethod
    def _error(message: str) -> G2PRegistryException:
        return G2PRegistryException(
            code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
            message=message,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC).replace(tzinfo=None)

    @staticmethod
    def _get_path(payload: Any, path: str) -> Any:
        current = payload
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    @classmethod
    def _map_claims(cls, claims: dict[str, Any], provider: G2PRegistrantAuthenticationProvider) -> dict[str, Any]:
        config = provider.provider_config or {}
        mapping = config.get("claim_mapping") or {}
        if not isinstance(mapping, dict):
            raise cls._error("Authentication provider claim_mapping must be an object.")
        mapped: dict[str, Any] = {}
        for field, claim_path in mapping.items():
            if not isinstance(field, str) or not isinstance(claim_path, str):
                continue
            value = cls._get_path(claims, claim_path)
            if value is not None and value != "":
                mapped[field] = value
        return mapped

    @staticmethod
    def _provider_to_login_provider(provider: G2PRegistrantAuthenticationProvider):
        return G2PRegistrantAuthenticationService._provider_to_login_provider(provider)

    async def _provider(self, session, provider_id: str) -> G2PRegistrantAuthenticationProvider:
        provider = await session.get(G2PRegistrantAuthenticationProvider, provider_id)
        if not provider:
            raise self._error("Authentication provider not found.")
        if not provider.is_active:
            raise self._error("Authentication provider is inactive.")
        return provider

    async def start(
        self,
        *,
        register_id: str,
        form_id: str,
        submission_id: str | None,
        provider_id: str,
        created_by: str,
    ) -> dict[str, Any]:
        from ..models.intake_identity import (
            OANIntakeIdentityAttempt,
            OANIntakeIdentityContext,
        )

        session_maker = get_async_session_maker()
        async with session_maker() as session:
            if submission_id:
                submission = await session.get(G2PIntakeFormSubmission, submission_id)
                if not submission:
                    raise self._error("Draft submission not found.")
                if submission.created_by != created_by:
                    raise self._error("Draft submission belongs to another staff principal.")
                if submission.form_id != form_id or submission.register_id != register_id:
                    raise self._error("Draft submission does not match the requested intake form.")

            provider = await self._provider(session, provider_id)
            context = OANIntakeIdentityContext(
                submission_id=submission_id,
                form_id=form_id,
                register_id=register_id,
                created_by=created_by,
                provider_id=provider.provider_id,
            )
            attempt = OANIntakeIdentityAttempt(context_id=context.context_id)
            session.add_all([context, attempt])
            await session.flush()

            login_provider = self._provider_to_login_provider(provider)
            adapter = self._adapters.resolve_for_provider(login_provider)
            auth_tx = self._auth_tx_store.create(
                login_provider_id=login_provider.id,
                redirect_uri=provider.oauth_callback_url,
                server_metadata=None,
                context={
                    "context_id": context.context_id,
                    "attempt_id": attempt.attempt_id,
                    "register_id": register_id,
                    "form_id": form_id,
                    "submission_id": submission_id,
                    "created_by": created_by,
                },
            )
            authorization_url, _ = await adapter.build_authorize_redirect(
                login_provider=login_provider,
                state=auth_tx.state,
                nonce=auth_tx.nonce,
                code_verifier=auth_tx.code_verifier,
            )
            await session.commit()
            return {
                "context_id": context.context_id,
                "authorization_url": authorization_url,
                "provider_name": provider.provider_name,
            }

    async def mock_verify(
        self,
        *,
        register_id: str,
        form_id: str,
        submission_id: str | None,
        provider_id: str,
        fayda_id: str,
        created_by: str,
    ) -> dict[str, Any]:
        """Complete a local-only mock Fayda verification for the intake UI."""
        from ..models.intake_identity import (
            OANIntakeIdentityAttempt,
            OANIntakeIdentityContext,
        )

        normalized_id = fayda_id.strip()
        claims = _MOCK_FAYDA_RECORDS.get(normalized_id)
        if not claims:
            raise self._error("Unknown mock Fayda ID. Copy one from mock-fayda.html.")

        session_maker = get_async_session_maker()
        async with session_maker() as session:
            if submission_id:
                submission = await session.get(G2PIntakeFormSubmission, submission_id)
                if not submission:
                    raise self._error("Draft submission not found.")
                if submission.created_by != created_by:
                    raise self._error("Draft submission belongs to another staff principal.")
                if submission.form_id != form_id or submission.register_id != register_id:
                    raise self._error("Draft submission does not match the requested intake form.")

            context = OANIntakeIdentityContext(
                submission_id=submission_id,
                form_id=form_id,
                register_id=register_id,
                created_by=created_by,
                provider_id=provider_id,
                status="VERIFIED",
                issuer=_MOCK_FAYDA_ISSUER,
                subject=f"mock-fayda:{normalized_id}",
                mapped_snapshot=claims,
                protected_fields=sorted(claims),
                expires_at=self._now() + timedelta(hours=24),
                completed_at=self._now(),
                updated_at=self._now(),
            )
            attempt = OANIntakeIdentityAttempt(
                context_id=context.context_id,
                status="VERIFIED",
                issuer=_MOCK_FAYDA_ISSUER,
                subject=f"mock-fayda:{normalized_id}",
                encrypted_claims=self._crypto.encrypt(claims),
                authentication_method="mock-fayda",
                claim_verifications={field: True for field in claims},
                token_hash=hashlib.sha256(f"mock-fayda:{normalized_id}".encode()).hexdigest(),
                completed_at=self._now(),
            )
            context.evidence_reference = f"mock-fayda:{context.context_id}:{attempt.attempt_id}"
            session.add_all([context, attempt])
            await session.commit()
            return {
                "context_id": context.context_id,
                "status": context.status,
                "mapped_values": claims,
                "protected_fields": context.protected_fields,
                "evidence_reference": context.evidence_reference,
                "issuer": context.issuer,
                "subject": context.subject,
                "expires_at": context.expires_at,
            }

    async def complete(self, *, code: str, state: str) -> dict[str, Any]:
        from ..models.intake_identity import (
            OANIntakeIdentityAttempt,
            OANIntakeIdentityContext,
        )

        auth_tx = self._auth_tx_store.get_and_pop(state)
        if not auth_tx:
            raise self._error("Invalid or expired authentication session.")
        context_data = auth_tx.context or {}
        context_id = context_data.get("context_id")
        attempt_id = context_data.get("attempt_id")

        session_maker = get_async_session_maker()
        async with session_maker() as session:
            context = await session.get(OANIntakeIdentityContext, context_id)
            attempt = await session.get(OANIntakeIdentityAttempt, attempt_id)
            if not context or not attempt:
                raise self._error("Authentication context not found.")
            provider = await self._provider(session, context.provider_id)
            try:
                login_provider = self._provider_to_login_provider(provider)
                adapter = self._adapters.resolve_for_provider(login_provider)
                crypto_helper = None
                if login_provider.token_endpoint_auth_method == TokenEndpointAuthMethod.private_key_jwt_keymanager:
                    crypto_helper = CryptoFactory.get()
                token_response = await adapter.exchange_code_for_token(
                    login_provider=login_provider,
                    code=code,
                    code_verifier=auth_tx.code_verifier,
                    keymanager_helper=crypto_helper,
                    km_app_id=provider.keymanager_sign_app_id,
                )
                await adapter.validate_callback_id_token(
                    login_provider=login_provider,
                    token_response=token_response,
                    nonce=auth_tx.nonce,
                )
                id_token = token_response.get("id_token")
                if not id_token:
                    raise self._error("Provider response did not contain an id_token.")
                claims = await adapter.oidc_client.decode_jwt(
                    login_provider=login_provider,
                    token=id_token,
                    nonce=auth_tx.nonce,
                    access_token=token_response.get("access_token"),
                )
                claims = await adapter.enrich_claims_from_userinfo(
                    claims,
                    login_provider=login_provider,
                    access_token=token_response.get("access_token"),
                )
                claims = adapter.normalize_claims(claims, login_provider=login_provider)
                adapter.validate_claims(claims, login_provider=login_provider)
                mapped = self._map_claims(claims, provider)
                context.status = "VERIFIED"
                context.issuer = str(claims.get("iss")) if claims.get("iss") is not None else None
                context.subject = adapter.registrant_subject(claims, login_provider=login_provider)
                context.mapped_snapshot = mapped
                context.protected_fields = sorted(mapped)
                context.evidence_reference = f"esignet:{context.context_id}:{attempt.attempt_id}"
                context.expires_at = self._now() + timedelta(hours=24)
                context.completed_at = self._now()
                context.updated_at = self._now()
                attempt.status = "VERIFIED"
                attempt.issuer = context.issuer
                attempt.subject = context.subject
                attempt.encrypted_claims = self._crypto.encrypt(claims)
                attempt.authentication_method = adapter.get_authentication_method(
                    claims, login_provider=login_provider
                )
                attempt.claim_verifications = adapter.get_claim_verifications(
                    claims, login_provider=login_provider
                )
                attempt.token_hash = hashlib.sha256(id_token.encode("utf-8")).hexdigest()
                attempt.completed_at = self._now()
                session.add_all([context, attempt])
                await session.commit()
                return {
                    "context_id": context.context_id,
                    "status": context.status,
                    "evidence_reference": context.evidence_reference,
                    "post_message_origin": (provider.provider_config or {}).get("post_message_origin"),
                }
            except Exception as exc:
                _logger.exception("Farmer intake authentication completion failed")
                attempt.status = "FAILED"
                attempt.failure_reason = str(exc)
                attempt.completed_at = self._now()
                context.status = "FAILED"
                context.updated_at = self._now()
                session.add_all([context, attempt])
                await session.commit()
                raise

    async def get_status(self, context_id: str, created_by: str) -> dict[str, Any]:
        from ..models.intake_identity import OANIntakeIdentityContext

        session_maker = get_async_session_maker()
        async with session_maker() as session:
            context = await session.get(OANIntakeIdentityContext, context_id)
            if not context or context.created_by != created_by:
                raise self._error("Authentication context not found.")
            if context.status == "VERIFIED" and context.expires_at and context.expires_at <= self._now():
                context.status = "EXPIRED"
                context.updated_at = self._now()
                session.add(context)
                await session.commit()
            return {
                "context_id": context.context_id,
                "status": context.status,
                "mapped_values": context.mapped_snapshot or {},
                "protected_fields": context.protected_fields or [],
                "evidence_reference": context.evidence_reference,
                "issuer": context.issuer,
                "subject": context.subject,
                "expires_at": context.expires_at,
            }

    async def reset(self, context_id: str, created_by: str) -> dict[str, Any]:
        from ..models.intake_identity import OANIntakeIdentityContext

        session_maker = get_async_session_maker()
        async with session_maker() as session:
            context = await session.get(OANIntakeIdentityContext, context_id)
            if not context or context.created_by != created_by:
                raise self._error("Authentication context not found.")
            context.status = "RESET"
            context.mapped_snapshot = None
            context.protected_fields = None
            context.evidence_reference = None
            context.issuer = None
            context.subject = None
            context.expires_at = None
            context.updated_at = self._now()
            session.add(context)
            await session.commit()
            return {"context_id": context.context_id, "status": context.status}

    async def bind_and_validate_record(
        self,
        *,
        record: dict[str, Any],
        submission_id: str,
        form_id: str,
        register_id: str,
        created_by: str,
        session,
    ) -> None:
        from ..models.intake_identity import OANIntakeIdentityContext

        context_id = record.get("intake_identity_context_id")
        if not context_id:
            return
        context = await session.get(OANIntakeIdentityContext, str(context_id))
        if not context or context.created_by != created_by:
            raise self._error("Authentication context is not owned by this staff principal.")
        if context.form_id != form_id or context.register_id != register_id:
            raise self._error("Authentication context does not match this Farmer intake form.")
        if context.status != "VERIFIED" or not context.expires_at or context.expires_at <= self._now():
            raise self._error("Authentication proof is missing or expired.")
        if context.submission_id and context.submission_id != submission_id:
            raise self._error("Authentication context is already bound to another submission.")
        context.submission_id = submission_id
        context.updated_at = self._now()
        record["identity_evidence_reference"] = context.evidence_reference
        for field in context.protected_fields or []:
            expected = (context.mapped_snapshot or {}).get(field)
            if field in record and record[field] not in (None, "", expected):
                raise self._error(f"Protected identity field '{field}' was changed.")
        session.add(context)

    async def validate_finalization(self, submission_id: str, session) -> None:
        from openg2p_registry_farmer_extension.register_domain.models.farmer import (
            G2PIntakeFormFarmer,
        )

        from ..models.intake_identity import OANIntakeIdentityContext

        row = (
            await session.execute(
                select(G2PIntakeFormFarmer).where(G2PIntakeFormFarmer.submission_id == submission_id)
            )
        ).scalars().first()
        if not row:
            return
        context_id = getattr(row, "intake_identity_context_id", None)
        if context_id:
            context = await session.get(OANIntakeIdentityContext, context_id)
            if not context or context.status != "VERIFIED" or not context.expires_at or context.expires_at <= self._now():
                raise self._error("Verified identity proof is missing or expired.")
            return
        identity_type = getattr(row, "identity_document_type", None)
        documents = (
            await session.execute(
                select(G2PIntakeFormSubmissionDocument).where(
                    G2PIntakeFormSubmissionDocument.submission_id == submission_id,
                    G2PIntakeFormSubmissionDocument.section_id == _FARMER_DOCUMENT_SECTION,
                )
            )
        ).scalars().all()
        has_identity_attachment = any(doc.label in _IDENTITY_DOCUMENT_LABELS for doc in documents)
        if not identity_type or not has_identity_attachment:
            raise self._error("Manual Farmer intake requires an identity document type and attachment.")
