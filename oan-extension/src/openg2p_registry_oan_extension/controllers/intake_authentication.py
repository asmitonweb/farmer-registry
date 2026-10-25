import html
import json
import logging
from datetime import datetime

from fastapi import Query, Request
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController
from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
    G2PResponse,
    G2PResponseBody,
    G2PResponseHeader,
    G2PResponseStatus,
)
from pydantic import BaseModel

from ..register_domain.services import OANIntakeIdentityService

_logger = logging.getLogger("oan-intake-auth-controller")


class IntakeAuthStartPayload(BaseModel):
    register_id: str
    form_id: str
    provider_id: str
    submission_id: str | None = None


class IntakeAuthStartBody(G2PRequestBody):
    request_payload: IntakeAuthStartPayload


class IntakeAuthStartRequest(G2PRequest):
    request_body: IntakeAuthStartBody


class IntakeAuthContextPayload(BaseModel):
    context_id: str


class IntakeAuthContextBody(G2PRequestBody):
    request_payload: IntakeAuthContextPayload


class IntakeAuthContextRequest(G2PRequest):
    request_body: IntakeAuthContextBody


class IntakeAuthMockVerifyPayload(BaseModel):
    register_id: str
    form_id: str
    provider_id: str
    fayda_id: str
    submission_id: str | None = None


class IntakeAuthMockVerifyBody(G2PRequestBody):
    request_payload: IntakeAuthMockVerifyPayload


class IntakeAuthMockVerifyRequest(G2PRequest):
    request_body: IntakeAuthMockVerifyBody


def _response(request: G2PRequest | None, payload: dict | None, status: G2PResponseStatus) -> G2PResponse:
    request_id = request.request_header.request_id if request else ""
    return G2PResponse(
        response_header=G2PResponseHeader(
            request_id=request_id,
            response_status=status,
            response_error_code="" if status == G2PResponseStatus.SUCCESS else "INVALID_REQUEST",
            response_error_message="" if status == G2PResponseStatus.SUCCESS else "Request could not be completed.",
            response_timestamp=datetime.now(),
        ),
        response_body=G2PResponseBody(response_payload=payload),
    )


class OANIntakeAuthenticationController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["/intake-auth"]
        self.router.add_api_route("/intake-auth/start", self.start, methods=["POST"])
        self.router.add_api_route("/intake-auth/callback", self.callback, methods=["GET"])
        self.router.add_api_route("/intake-auth/status", self.status, methods=["POST"])
        self.router.add_api_route("/intake-auth/reset", self.reset, methods=["POST"])
        self.router.add_api_route("/intake-auth/mock-verify", self.mock_verify, methods=["POST"])
        self.service = OANIntakeIdentityService.get_component()

    @require_permissions({"intakeSubmission:edit"})
    async def start(self, request: Request, g2p_request: IntakeAuthStartRequest):
        try:
            payload = g2p_request.request_body.request_payload
            created_by = getattr(request.state.auth, "name", "Unknown")
            result = await self.service.start(
                register_id=payload.register_id,
                form_id=payload.form_id,
                submission_id=payload.submission_id,
                provider_id=payload.provider_id,
                created_by=created_by,
            )
            return _response(g2p_request, result, G2PResponseStatus.SUCCESS)
        except Exception:
            _logger.exception("Failed to start Farmer intake authentication")
            return _response(g2p_request, None, G2PResponseStatus.ERROR)

    @require_permissions({"intakeSubmission:edit"})
    async def mock_verify(self, request: Request, g2p_request: IntakeAuthMockVerifyRequest):
        try:
            payload = g2p_request.request_body.request_payload
            created_by = getattr(request.state.auth, "name", "Unknown")
            result = await self.service.mock_verify(
                register_id=payload.register_id,
                form_id=payload.form_id,
                submission_id=payload.submission_id,
                provider_id=payload.provider_id,
                fayda_id=payload.fayda_id,
                created_by=created_by,
            )
            return _response(g2p_request, result, G2PResponseStatus.SUCCESS)
        except Exception:
            _logger.exception("Failed to complete mock Farmer intake authentication")
            return _response(g2p_request, None, G2PResponseStatus.ERROR)

    async def callback(self, code: str = Query(...), state: str = Query(...)):
        try:
            result = await self.service.complete(code=code, state=state)
            context_id = html.escape(str(result.get("context_id", "")), quote=True)
            origin = result.get("post_message_origin") or "null"
            if origin != "null":
                origin = json.dumps(str(origin))
            return self._callback_html(context_id, result.get("status", "FAILED"), origin)
        except Exception:
            _logger.exception("Failed to complete Farmer intake authentication")
            return self._callback_html("", "FAILED", "null")

    @require_permissions({"intakeSubmission:edit"})
    async def status(self, request: Request, g2p_request: IntakeAuthContextRequest):
        try:
            context_id = g2p_request.request_body.request_payload.context_id
            created_by = getattr(request.state.auth, "name", "Unknown")
            result = await self.service.get_status(context_id, created_by)
            return _response(g2p_request, result, G2PResponseStatus.SUCCESS)
        except Exception:
            _logger.exception("Failed to read Farmer intake authentication status")
            return _response(g2p_request, None, G2PResponseStatus.ERROR)

    @require_permissions({"intakeSubmission:edit"})
    async def reset(self, request: Request, g2p_request: IntakeAuthContextRequest):
        try:
            context_id = g2p_request.request_body.request_payload.context_id
            created_by = getattr(request.state.auth, "name", "Unknown")
            result = await self.service.reset(context_id, created_by)
            return _response(g2p_request, result, G2PResponseStatus.SUCCESS)
        except Exception:
            _logger.exception("Failed to reset Farmer intake authentication")
            return _response(g2p_request, None, G2PResponseStatus.ERROR)

    @staticmethod
    def _callback_html(context_id: str, status: str, origin: str) -> str:
        safe_status = html.escape(str(status), quote=True)
        target = origin if origin != "null" else "window.location.origin"
        return f"""<!doctype html>
<html><body><p>Identity verification {safe_status.lower()}.</p>
<script>
window.opener?.postMessage({{type:'oan:intake-auth:complete',contextId:'{context_id}',status:'{safe_status}'}},{target});
window.close();
</script></body></html>"""
