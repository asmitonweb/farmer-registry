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

from sqlalchemy import Boolean, Numeric, String, Text

# register mnemonic -> {field: (column type, python type)}
OAN_FIELDS: dict[str, dict[str, tuple]] = {
    "Farmer": {
        # The same names in Ethiopic and Afaan Oromo script.
        "first_name_amh": (String, str),
        "middle_name_amh": (String, str),
        "last_name_amh": (String, str),
        "first_name_om": (String, str),
        "middle_name_om": (String, str),
        "last_name_om": (String, str),
        # The father's own names.
        "father_first_name": (String, str),
        "father_middle_name": (String, str),
        "father_last_name": (String, str),
        # Productive Safety Net Programme beneficiary.
        "is_psnp_user": (Boolean, bool),
    },
    "Land": {
        "land_id": (String, str),  # farmer-assigned or external parcel identifier
        "remark": (Text, str),
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
