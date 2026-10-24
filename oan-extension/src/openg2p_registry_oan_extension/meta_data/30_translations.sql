-- Labels for the OAN widgets and panels, merged into each language's domain
-- translations. Upstream keys win where both define one, so this only adds.
-- A language listed here that the registry does not have is skipped.

WITH oan (language_code, labels) AS (
  VALUES ('en', '{
    "names_in_amharic": "Names in Amharic",
    "names_in_afaan_oromo": "Names in Afaan Oromo",
    "father_name": "Father''s Name",
    "first_name_amh": "First Name (Amharic)",
    "middle_name_amh": "Middle Name (Amharic)",
    "last_name_amh": "Last Name (Amharic)",
    "first_name_om": "First Name (Afaan Oromo)",
    "middle_name_om": "Middle Name (Afaan Oromo)",
    "last_name_om": "Last Name (Afaan Oromo)",
    "father_first_name": "Father''s First Name",
    "father_middle_name": "Father''s Middle Name",
    "father_last_name": "Father''s Last Name",
    "ethiopic_script_only": "Use Ethiopic (Ge''ez) script",
    "latin_script_only": "Use Latin letters",
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
