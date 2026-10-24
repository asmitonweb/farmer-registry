"""OAN columns on upstream registers.

Only data the upstream models have no field for. Everything else maps onto an
upstream or core column (language_spoken, phone_numbers, the G2PGeo location
and coordinates, land_size + unit, household_member.is_head), is derived when
shown (Ethiopic dates, land totals), or is a supporting-document slot in the
section metadata. Each mixin is added to its register's three ORM classes.
"""

from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class OANFarmer:

    # The same names in Ethiopic and Afaan Oromo script, beside the base
    # G2PPerson names.
    first_name_amh: Mapped[str] = mapped_column(String, nullable=True)
    middle_name_amh: Mapped[str] = mapped_column(String, nullable=True)
    last_name_amh: Mapped[str] = mapped_column(String, nullable=True)
    first_name_om: Mapped[str] = mapped_column(String, nullable=True)
    middle_name_om: Mapped[str] = mapped_column(String, nullable=True)
    last_name_om: Mapped[str] = mapped_column(String, nullable=True)

    # The father's own names. With first_name they identify the farmer.
    father_first_name: Mapped[str] = mapped_column(String, nullable=True)
    father_middle_name: Mapped[str] = mapped_column(String, nullable=True)
    father_last_name: Mapped[str] = mapped_column(String, nullable=True)

    is_psnp_user: Mapped[bool] = mapped_column(Boolean, nullable=True)  # Productive Safety Net Programme


class OANLand:

    land_id: Mapped[str] = mapped_column(String, nullable=True)  # farmer-assigned or external parcel identifier
    remark: Mapped[str] = mapped_column(Text, nullable=True)


class OANLivestock:

    gender: Mapped[str] = mapped_column(String, nullable=True)            # Attribute lookup
    body_condition: Mapped[str] = mapped_column(String, nullable=True)    # Attribute lookup
    production_type: Mapped[str] = mapped_column(String, nullable=True)   # Attribute lookup


class OANFarmInputs:

    amount_fertilizer_utilized: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    amount_pesticide_utilized: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    amount_insecticide_utilized: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)
    amount_improved_seed_utilized: Mapped[float] = mapped_column(Numeric(12, 3), nullable=True)


class OANMembershipDetails:

    primary_commodity: Mapped[str] = mapped_column(String, nullable=True)  # Attribute lookup: the cluster's focal commodity
