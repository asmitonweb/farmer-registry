-- Fail loudly when the OAN layer did not apply. The seed runs psql with
-- ON_ERROR_STOP=0, so a derivation that matched nothing (an upstream section
-- renamed or reshaped) would otherwise pass silently. This raises an ERROR in
-- the seed log naming what is missing.

DO $$
DECLARE
  missing text;
BEGIN
  SELECT string_agg(f, ', ') INTO missing
  FROM (VALUES
    ('oan_farmer_personal_identification', 'first_name_amh'),
    ('oan_farmer_personal_identification', 'last_name_other'),
    ('oan_farmer_personal_identification', 'language_spoken'),
    ('oan_farmer_personal_identification', 'birth_date'),
    ('oan_farmer_photo', 'farmer-photo'),
    ('oan_farmer_socio_economic_and_health', 'is_psnp_user'),
    ('oan_farmer_membership_details', 'primary_commodity'),
    ('oan_farmer_lands', 'land_id'),
    ('oan_farmer_lands', 'remark'),
    ('oan_farmer_livestock', 'production_type'),
    ('oan_farmer_livestock_intake', 'production_type'),
    ('oan_farmer_farm_inputs', 'amount_improved_seed_utilized'),
    ('oan_farmer_farm_inputs_intake', 'amount_improved_seed_utilized')
  ) e(section_id, field)
  CROSS JOIN LATERAL (SELECT e.section_id || '.' || e.field AS f) n
  WHERE NOT EXISTS (
    SELECT 1 FROM "public"."g2p_register_sections" s
    WHERE s.section_id = e.section_id
      AND jsonb_path_exists(s.section_ui_schema,
            'lax $.** ? (@."widget-id" == $f || @."column-key" == $f)',
            jsonb_build_object('f', e.field)));
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'OAN metadata layer incomplete, missing: %', missing;
  END IF;

  SELECT string_agg(section_id, ', ') INTO missing
  FROM (VALUES ('oan_farmer_personal_identification'), ('oan_farmer_socio_economic_and_health'),
               ('oan_farmer_membership_details'), ('oan_farmer_lands'), ('oan_farmer_livestock'),
               ('oan_farmer_farm_inputs')) e(section_id)
  WHERE NOT EXISTS (SELECT 1 FROM "public"."g2p_register_ui_tab_sections" t WHERE t.section_id = e.section_id);
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'OAN sections not on any register tab: %', missing;
  END IF;

  SELECT string_agg(section_id, ', ') INTO missing
  FROM (VALUES ('oan_farmer_personal_identification'), ('oan_farmer_socio_economic_and_health'),
               ('oan_farmer_membership_details'), ('oan_farmer_lands'), ('oan_farmer_livestock_intake'),
               ('oan_farmer_farm_inputs_intake'), ('oan_farmer_photo')) e(section_id)
  WHERE NOT EXISTS (SELECT 1 FROM "public"."g2p_intake_form_ui_tab_sections" t WHERE t.section_id = e.section_id);
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'OAN sections not on the intake form: %', missing;
  END IF;
END $$;
