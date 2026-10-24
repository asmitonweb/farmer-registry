# Everything the farmer extension provides, then OAN's additions below. Core
# resolves classes by name on this module, so a name defined here wins.
from openg2p_registry_farmer_extension.register_domain.models import *  # noqa: F401,F403
from openg2p_registry_farmer_extension.register_domain import models as _farmer
from sqlalchemy.orm import mapped_column

from ..fields import OAN_FIELDS


def _add_oan_columns() -> None:
    """Append each OAN field to the register, history and intake classes."""
    for mnemonic, fields in OAN_FIELDS.items():
        for prefix in ("G2PRegister", "G2PRegisterHistory", "G2PIntakeForm"):
            cls = getattr(_farmer, f"{prefix}{mnemonic}")
            for name, (column_type, _) in fields.items():
                if name not in cls.__table__.c:  # importing twice must not add twice
                    setattr(cls, name, mapped_column(column_type, nullable=True))


_add_oan_columns()
