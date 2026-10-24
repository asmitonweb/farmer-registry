-- Labels for the OAN widgets and panels, merged into each language's domain
-- translations. Upstream keys win where both define one, so this only adds.
-- A language listed here that the registry does not have is skipped.

WITH oan (language_code, labels) AS (
  VALUES ('en', '{
    "first_name_eng": "First Name (English)",
    "fathers_name_eng": "Father''s Name (English)",
    "grandfathers_name_eng": "Grandfather''s Name (English)",
    "first_name_amh": "First Name (Amharic)",
    "fathers_name_amh": "Father''s Name (Amharic)",
    "grandfathers_name_amh": "Grandfather''s Name (Amharic)",
    "first_name_other": "First Name (Primary Language)",
    "fathers_name_other": "Father''s Name (Primary Language)",
    "grandfathers_name_other": "Grandfather''s Name (Primary Language)",
    "primary_language": "Primary Language",
    "farmer_photo": "Farmer Photo",
    "ethiopic_script_only": "Use Ethiopic (Ge''ez) script",
    "is_psnp_user": "PSNP Beneficiary",
    "primary_commodity": "Primary Commodity",
    "land_id": "Land ID",
    "remark": "Remark",
    "gender": "Gender",
    "body_condition": "Body Condition",
    "production_type": "Production Type",
    "amount_fertilizer_utilized": "Fertilizer Used",
    "amount_pesticide_utilized": "Pesticide Used",
    "amount_insecticide_utilized": "Insecticide Used",
    "amount_improved_seed_utilized": "Improved Seed Used"
  }'::jsonb)
)
UPDATE "public"."registry_languages" l
SET "domain_translation" = (oan.labels || COALESCE(l."domain_translation"::jsonb, '{}'::jsonb))::json
FROM oan
WHERE l."language_code" = oan.language_code;
