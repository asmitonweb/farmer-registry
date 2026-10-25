"""Farmer intake service hooks for server-side identity-proof enforcement."""

from openg2p_fastapi_common.context import component_registry
from openg2p_registry_core.services.intake_form_data_service import (
    G2PIntakeFormDataService,
)
from openg2p_registry_farmer_extension.register_domain.services.g2p_intake_form_data_service_farmer import (
    G2PFarmerIntakeFormDataService,
)

from .intake_identity import OANIntakeIdentityService


class OANFarmerIntakeFormDataService(G2PFarmerIntakeFormDataService):
    async def save_intake_form_submission_with_session(
        self,
        submission_id,
        section_id,
        section_payload,
        section_register_id,
        form_id,
        register_id,
        created_by,
        session,
        documents=None,
    ):
        identity = OANIntakeIdentityService.get_component()
        draft = await self._get_or_create_draft_submission(
            submission_id,
            form_id,
            register_id,
            created_by,
            session,
        )
        actual_submission_id = draft.submission_id
        if register_id == "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd":
            for record in section_payload or []:
                if isinstance(record, dict):
                    await identity.bind_and_validate_record(
                        record=record,
                        submission_id=actual_submission_id,
                        form_id=form_id,
                        register_id=register_id,
                        created_by=created_by,
                        session=session,
                    )
        return await super().save_intake_form_submission_with_session(
            actual_submission_id,
            section_id,
            section_payload,
            section_register_id,
            form_id,
            register_id,
            created_by,
            session,
            documents=documents,
        )

    async def finalize_submission_with_session(
        self,
        submission_id,
        session,
        finalized_by=None,
        bearer_token=None,
        requester_sub=None,
    ):
        submission = await self._get_submission_or_error(submission_id, session)
        if submission.register_id == "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd":
            await OANIntakeIdentityService.get_component().validate_finalization(submission_id, session)
        return await super().finalize_submission_with_session(
            submission_id,
            session,
            finalized_by,
            bearer_token=bearer_token,
            requester_sub=requester_sub,
        )

    async def approve_submission_with_session(self, submission_id, session, approved_by=None):
        submission = await self._get_submission_or_error(submission_id, session)
        if submission.register_id == "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd":
            await OANIntakeIdentityService.get_component().validate_finalization(submission_id, session)
        return await super().approve_submission_with_session(submission_id, session, approved_by)


def install_oan_intake_service() -> None:
    instance = OANFarmerIntakeFormDataService()
    if instance in component_registry:
        component_registry.remove(instance)
    first = next(
        (i for i, component in enumerate(component_registry) if isinstance(component, G2PIntakeFormDataService)),
        len(component_registry),
    )
    component_registry.insert(first, instance)
