"""Pydantic mirrors of models/oan.py, added to the same registers' schemas."""

from typing import Optional


class OANSchemaFarmer:

    first_name_amh: Optional[str] = None
    middle_name_amh: Optional[str] = None
    last_name_amh: Optional[str] = None
    first_name_om: Optional[str] = None
    middle_name_om: Optional[str] = None
    last_name_om: Optional[str] = None
    father_first_name: Optional[str] = None
    father_middle_name: Optional[str] = None
    father_last_name: Optional[str] = None
    is_psnp_user: Optional[bool] = None


class OANSchemaLand:

    land_id: Optional[str] = None
    remark: Optional[str] = None


class OANSchemaLivestock:

    gender: Optional[str] = None
    body_condition: Optional[str] = None
    production_type: Optional[str] = None


class OANSchemaFarmInputs:

    amount_fertilizer_utilized: Optional[float] = None
    amount_pesticide_utilized: Optional[float] = None
    amount_insecticide_utilized: Optional[float] = None
    amount_improved_seed_utilized: Optional[float] = None


class OANSchemaMembershipDetails:

    primary_commodity: Optional[str] = None
