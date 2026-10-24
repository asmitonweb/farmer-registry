"""OAN fields on the farmer extension's registers, declared once.

The registry platform's rule for a field whose column does not exist is to add
it to the register's model mixin, so the register, history and intake tables all
get it, and to its Pydantic schema, then show it through the section metadata.
The farmer extension is upstream and is not edited, so this package does the
same from outside: models/ appends each column to the three mapped classes, and
schemas/ subclasses the register and intake schemas under their own names,
which is how core finds them. Everything else about a field (label, widget,
validation, dropdown list) is seed metadata.
"""

from datetime import date

from sqlalchemy import Boolean, Date, Numeric, String, Text

# register mnemonic -> {field: (column type, python type)}
OAN_FIELDS: dict[str, dict[str, tuple]] = {
    "Farmer": {
        # An Ethiopian name is the person's, the father's and the grandfather's
        # name, which upstream's first, middle and last name hold in English.
        # The same three names in Amharic, and in the farmer's primary language
        # (upstream's language_spoken) when that is not Amharic.
        "first_name_amh": (String, str),
        "middle_name_amh": (String, str),
        "last_name_amh": (String, str),
        "first_name_other": (String, str),
        "middle_name_other": (String, str),
        "last_name_other": (String, str),
        # Productive Safety Net Programme beneficiary.
        "is_psnp_user": (Boolean, bool),
        # Ethiopian calendar twin of birth_date, derived from it.
        "birth_date_ec": (String, str),
        # A second, local or community language (LANGUAGE list).
        "local_language": (String, str),
        "is_household_head": (Boolean, bool),
        # Identifiers, as attributes of the farmer (OpenG2P's advice for the
        # migration): the Fayda FIN is upstream's foundational_id; the Fayda
        # registration id (RID) until a FIN is issued; the ODK Farmer ID; and
        # the Pula (Mavuno) ID, for a later Pula update to the same farmer.
        "rid": (String, str),
        "odk_farmer_id": (String, str),
        "pula_id": (String, str),
        # Who collected the record, where and when: taken from the submission
        # and the enumerator's device, never typed on the form.
        "enumerator_name": (String, str),
        "enumerator_user_id": (String, str),
        "data_collection_date": (Date, date),
        "enumerator_latitude": (Numeric(10, 7), float),
        "enumerator_longitude": (Numeric(10, 7), float),
        "enumerator_altitude": (Numeric(10, 2), float),
        "enumerator_accuracy": (Numeric(10, 2), float),
        # Derived from the farmer's active lands, in hectares.
        "total_land_area": (Numeric(16, 6), float),
        "total_land_owned_area": (Numeric(16, 6), float),
        "total_land_rent_area": (Numeric(16, 6), float),
        "total_land_crop_sharing_area": (Numeric(16, 6), float),
        "land_ownership": (String, str),  # OWNER, TENANT or HYBRID
        # Names of the units in geo_code_hierarchy_json, for lists and search.
        "region_name": (String, str),
        "zone_name": (String, str),
        "woreda_name": (String, str),
        "kebele_name": (String, str),
    },
    "HouseholdMember": {
        "odk_member_id": (String, str),  # the ODK Member ID, as an attribute
    },
    "Household": {
        "father_included": (Boolean, bool),
        "mother_included": (Boolean, bool),
    },
    "Land": {
        "land_id": (String, str),  # farmer-assigned or external parcel identifier
        "remark": (Text, str),
        "land_kebele": (String, str),
        # Derived: land_size in hectares, and whether a certificate is on file.
        "area_in_hectare": (Numeric(16, 6), float),
        "certificate_provided": (Boolean, bool),
    },
    "Crop": {
        "planted_date_ec": (String, str),  # Ethiopian calendar twin of planted_date
    },
    "Livestock": {
        "gender": (String, str),  # attribute lookups
        "body_condition": (String, str),
        "production_type": (String, str),
    },
    "FarmInputs": {
        "amount_fertilizer_utilized": (Numeric(12, 3), float),
        "amount_pesticide_utilized": (Numeric(12, 3), float),
        "amount_insecticide_utilized": (Numeric(12, 3), float),
        "amount_improved_seed_utilized": (Numeric(12, 3), float),
    },
    "MembershipDetails": {
        "primary_commodity": (String, str),  # attribute lookup: the cluster's focal commodity
    },
}
