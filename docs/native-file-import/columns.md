# Farmer file-import columns

Dates and identifiers must be text cells. XLSX reads the active worksheet. Replace synthetic examples with deployment-specific values.

| Column | Group | Required | Description | Allowed values |
| --- | --- | --- | --- | --- |
| first_name | Personal | Yes | First name (English) |  |
| middle_name | Personal |  | Middle name (English) |  |
| last_name | Personal |  | Last name (English) |  |
| first_name_amh | Personal |  | First name (Amharic) |  |
| middle_name_amh | Personal |  | Middle name (Amharic) |  |
| last_name_amh | Personal |  | Last name (Amharic) |  |
| first_name_om | Personal |  | First name (Afaan Oromo) |  |
| middle_name_om | Personal |  | Middle name (Afaan Oromo) |  |
| last_name_om | Personal |  | Last name (Afaan Oromo) |  |
| father_first_name | Personal | Yes | Father's first name |  |
| father_middle_name | Personal |  | Father's middle name |  |
| father_last_name | Personal |  | Father's last name |  |
| gender | Personal |  | Gender | MALE, FEMALE, UNKNOWN |
| birth_date | Personal |  | Date of birth (Gregorian) YYYY-MM-DD |  |
| birth_date_ec | Personal |  | Date of birth (Ethiopian) YYYY-MM-DD |  |
| estimated_age | Personal |  | Age in years if birth date unknown |  |
| marital_status | Socio-economic |  | Marital status | SINGLE, MARRIED, DIVORCED, WIDOWED |
| education_level | Socio-economic |  | Education level | ILLITERATE, CAN_READ_AND_WRITE, BASIC, INTERMEDIARY, HIGHER_EDUCATION |
| source_of_income | Socio-economic |  | Main source of income | CROP_PRODUCTION, LIVESTOCK_PRODUCTION, GOVERNMENT_NGO_SUPPORT, OTHERS |
| source_of_income_other | Socio-economic |  | Describe income source when OTHERS |  |
| is_psnp_user | Socio-economic |  | Productive Safety Net Programme beneficiary | yes, no |
| is_household_head | Socio-economic |  | Is household head | yes, no |
| disabled | Socio-economic |  | Has a disability | yes, no |
| disability_type | Socio-economic |  | Disability type (if disabled) | VISION, HEARING, MOBILITY, COGNITION, SELF_CARE, COMMUNICATION |
| disability_severity | Socio-economic |  | Disability severity (if disabled) | NO_DIFFICULTY, SOME_DIFFICULTY, A_LOT_OF_DIFFICULTY, CANNOT_DO_AT_ALL |
| language_spoken | Socio-economic |  | Primary language spoken |  |
| local_language | Socio-economic |  | Local/community language |  |
| national_fan | Identification |  | National FAN / UID (no spaces) |  |
| national_rid | Identification |  | National RID |  |
| region_name | Location |  | Region |  |
| zone_name | Location |  | Zone |  |
| woreda_name | Location |  | Woreda |  |
| kebele_name | Location |  | Kebele |  |
| latitude | Location |  | Latitude (decimal degrees) |  |
| longitude | Location |  | Longitude (decimal degrees) |  |
| phone_1 | Phone |  | Phone number 1 |  |
| phone_2 | Phone |  | Phone number 2 |  |
| is_primary_cooperative_member | Membership |  | Member of a primary cooperative | yes, no |
| primary_cooperative_name | Membership |  | Primary cooperative name |  |
| is_cooperative_union_member | Membership |  | Member of a cooperative union | yes, no |
| cooperative_union_name | Membership |  | Cooperative union name |  |
| is_farmer_cluster_member | Membership |  | Member of a farmer cluster | yes, no |
| farmer_cluster_role | Membership |  | Cluster role | LEAD, DEPUTY, SECRETARY, ACCOUNTANT, MEMBER |
| primary_commodity | Membership |  | Cluster focal commodity |  |
| fertilizer_use | Farm inputs |  | Uses fertilizer | yes, no |
| amount_fertilizer_utilized | Farm inputs |  | Fertilizer amount (kg) |  |
| pesticide_use | Farm inputs |  | Uses pesticide | yes, no |
| amount_pesticide_utilized | Farm inputs |  | Pesticide amount |  |
| insecticide_use | Farm inputs |  | Uses insecticide | yes, no |
| amount_insecticide_utilized | Farm inputs |  | Insecticide amount |  |
| improved_seed_use | Farm inputs |  | Uses improved seed | yes, no |
| amount_improved_seed_utilized | Farm inputs |  | Improved seed amount (kg) |  |
| water_source | Farm inputs |  | Water source |  |
| access_to_machinery | Farm inputs |  | Has access to machinery | yes, no |
| access_to_finance | Farm inputs |  | Has access to finance | yes, no |
| land_1_id | Land 1 |  | Parcel identifier |  |
| land_1_ownership | Land 1 |  | Ownership type | OWNER, TENANT, CROP_SHARE, FAMILY_GIFT |
| land_1_area_ha | Land 1 |  | Total area in hectares |  |
| land_1_kebele | Land 1 |  | Kebele of the parcel |  |
| land_1_current_use | Land 1 |  | Current land use | AGRICULTURAL, RESIDENTIAL, GRAZING, FOREST |
| land_2_id | Land 2 |  | Parcel identifier |  |
| land_2_ownership | Land 2 |  | Ownership type | OWNER, TENANT, CROP_SHARE, FAMILY_GIFT |
| land_2_area_ha | Land 2 |  | Total area in hectares |  |
| land_2_kebele | Land 2 |  | Kebele of the parcel |  |
| land_2_current_use | Land 2 |  | Current land use | AGRICULTURAL, RESIDENTIAL, GRAZING, FOREST |
| land_3_id | Land 3 |  | Parcel identifier |  |
| land_3_ownership | Land 3 |  | Ownership type | OWNER, TENANT, CROP_SHARE, FAMILY_GIFT |
| land_3_area_ha | Land 3 |  | Total area in hectares |  |
| land_3_kebele | Land 3 |  | Kebele of the parcel |  |
| land_3_current_use | Land 3 |  | Current land use | AGRICULTURAL, RESIDENTIAL, GRAZING, FOREST |
| crop_1_name | Crop 1 |  | Crop / commodity |  |
| crop_1_planted_date | Crop 1 |  | Planted date YYYY-MM-DD |  |
| crop_1_season | Crop 1 |  | Season code from configured master data |  |
| crop_1_end_use | Crop 1 |  | End use | FOOD_HUMAN_CONSUMPTION, FEED_ANIMALS, BIOFUELS_NONFOOD, OTHER |
| crop_2_name | Crop 2 |  | Crop / commodity |  |
| crop_2_planted_date | Crop 2 |  | Planted date YYYY-MM-DD |  |
| crop_2_season | Crop 2 |  | Season code from configured master data |  |
| crop_2_end_use | Crop 2 |  | End use | FOOD_HUMAN_CONSUMPTION, FEED_ANIMALS, BIOFUELS_NONFOOD, OTHER |
| crop_3_name | Crop 3 |  | Crop / commodity |  |
| crop_3_planted_date | Crop 3 |  | Planted date YYYY-MM-DD |  |
| crop_3_season | Crop 3 |  | Season code from configured master data |  |
| crop_3_end_use | Crop 3 |  | End use | FOOD_HUMAN_CONSUMPTION, FEED_ANIMALS, BIOFUELS_NONFOOD, OTHER |
| livestock_1_type | Livestock 1 |  | Animal type |  |
| livestock_1_head_count | Livestock 1 |  | Number of animals |  |
| livestock_1_system | Livestock 1 |  | Livestock system | NOMADIC_PASTORAL, SEMI_NOMADIC, SEDENTARY_PASTORAL, MIXED, INDUSTRIAL |
| livestock_2_type | Livestock 2 |  | Animal type |  |
| livestock_2_head_count | Livestock 2 |  | Number of animals |  |
| livestock_2_system | Livestock 2 |  | Livestock system | NOMADIC_PASTORAL, SEMI_NOMADIC, SEDENTARY_PASTORAL, MIXED, INDUSTRIAL |
| livestock_3_type | Livestock 3 |  | Animal type |  |
| livestock_3_head_count | Livestock 3 |  | Number of animals |  |
| livestock_3_system | Livestock 3 |  | Livestock system | NOMADIC_PASTORAL, SEMI_NOMADIC, SEDENTARY_PASTORAL, MIXED, INDUSTRIAL |
| member_1_name | Household member 1 |  | Full name (first middle last) |  |
| member_1_gender | Household member 1 |  | Gender | MALE, FEMALE, UNKNOWN |
| member_1_birth_date | Household member 1 |  | Birth date YYYY-MM-DD |  |
| member_1_is_disabled | Household member 1 |  | Has a disability | yes, no |
| member_2_name | Household member 2 |  | Full name (first middle last) |  |
| member_2_gender | Household member 2 |  | Gender | MALE, FEMALE, UNKNOWN |
| member_2_birth_date | Household member 2 |  | Birth date YYYY-MM-DD |  |
| member_2_is_disabled | Household member 2 |  | Has a disability | yes, no |
| member_3_name | Household member 3 |  | Full name (first middle last) |  |
| member_3_gender | Household member 3 |  | Gender | MALE, FEMALE, UNKNOWN |
| member_3_birth_date | Household member 3 |  | Birth date YYYY-MM-DD |  |
| member_3_is_disabled | Household member 3 |  | Has a disability | yes, no |
| member_4_name | Household member 4 |  | Full name (first middle last) |  |
| member_4_gender | Household member 4 |  | Gender | MALE, FEMALE, UNKNOWN |
| member_4_birth_date | Household member 4 |  | Birth date YYYY-MM-DD |  |
| member_4_is_disabled | Household member 4 |  | Has a disability | yes, no |
| member_5_name | Household member 5 |  | Full name (first middle last) |  |
| member_5_gender | Household member 5 |  | Gender | MALE, FEMALE, UNKNOWN |
| member_5_birth_date | Household member 5 |  | Birth date YYYY-MM-DD |  |
| member_5_is_disabled | Household member 5 |  | Has a disability | yes, no |
| enumerator_name | Enumerator |  | Data collector name |  |
| enumerator_user_id | Enumerator |  | Data collector id |  |
| data_collection_date | Enumerator |  | Collection date YYYY-MM-DD |  |
