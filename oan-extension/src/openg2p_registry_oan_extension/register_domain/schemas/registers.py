
from openg2p_registry_core.schemas import (
    G2PIntakeFormSchemaBase,
    G2PRegisterBaseSchema,
    G2PRegisterHistorySchema,
)


class G2PSchemaFarmerPhone:
    phone_type: str | None = None
    phone_number: str | None = None
    country_code: str | None = None
    is_primary: bool | None = None
    phone_e164: str | None = None


class G2PRegisterSchemaFarmerPhone(G2PRegisterBaseSchema, G2PSchemaFarmerPhone):
    """A farmer's phone number."""


class G2PRegisterHistorySchemaFarmerPhone(G2PRegisterHistorySchema):
    """History of a farmer's phone number."""


class G2PIntakeFormSchemaFarmerPhone(G2PIntakeFormSchemaBase, G2PRegisterBaseSchema, G2PSchemaFarmerPhone):
    """A farmer's phone number on the intake form."""


class G2PSchemaFarmerName:
    language: str | None = None
    language_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None


class G2PRegisterSchemaFarmerName(G2PRegisterBaseSchema, G2PSchemaFarmerName):
    """A farmer's name in a language other than English and Amharic."""


class G2PRegisterHistorySchemaFarmerName(G2PRegisterHistorySchema):
    """History of a farmer's name in another language."""


class G2PIntakeFormSchemaFarmerName(G2PIntakeFormSchemaBase, G2PRegisterBaseSchema, G2PSchemaFarmerName):
    """A farmer's name in another language on the intake form."""
