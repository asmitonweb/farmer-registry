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
    ('oan_farmer_farm_inputs_intake', 'amount_improved_seed_utilized'),
    ('oan_farmer_socio_economic_and_health', 'source_of_income_other'),
    ('oan_farmer_household_lookup', 'is_household_head'),
    ('oan_household_information', 'father_included'),
    ('oan_farmer_location', 'farmer_geo_point'),
    ('oan_farmer_location', 'local_language'),
    ('oan_farmer_location', 'farmer_geo_hierarchy'),
    ('oan_farmer_photo', 'enumerator-position'),
    ('oan_farmer_lands', 'certificate_storage_id'),
    ('oan_farmer_crops', 'is_diseased'),
    ('oan_farmer_crops_intake', 'disease_type'),
    ('oan_farmer_livestock_intake', 'collected_date'),
    ('oan_farmer_farm_inputs_intake', 'machinery_type'),
    ('oan_farmer_personal_identification', 'has_national_id'),
    ('oan_farmer_socio_economic_and_health', 'farming_type'),
    ('oan_household_information', 'other_farmer_in_household'),
    ('oan_farmer_documents', 'identity_document_1'),
    ('oan_farmer_documents', 'identity_document_type'),
    ('oan_farmer_phones', 'phone_number'),
    ('oan_farmer_personal_identification', 'foundational_id'),
    ('oan_farmer_personal_identification', 'rid'),
    ('oan_farmer_personal_identification', 'pula_id'),
    ('oan_farmer_land_summary', 'total_land_area'),
    ('oan_farmer_enumerator', 'enumerator_name')
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

  -- A form-layout widget naming an upstream widget-id that upstream no longer
  -- has comes out without a "widget" type (12_form_sections.sql).
  SELECT string_agg(DISTINCT s.section_id || '.' || (w->>'widget-id'), ', ') INTO missing
  FROM "public"."g2p_register_sections" s,
       jsonb_path_query(s.section_ui_schema, 'lax $.**.widgets[*]') w
  WHERE s.section_id LIKE 'oan\_%' AND NOT w ? 'widget';
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'OAN form layout names upstream widgets that do not exist: %', missing;
  END IF;

  SELECT string_agg(section_id, ', ') INTO missing
  FROM (VALUES ('oan_farmer_personal_identification'), ('oan_farmer_socio_economic_and_health'),
               ('oan_farmer_membership_details'), ('oan_farmer_lands'), ('oan_farmer_livestock'),
               ('oan_farmer_farm_inputs'), ('oan_farmer_household_lookup'), ('oan_household_information'),
               ('oan_farmer_location'), ('oan_farmer_crops'), ('oan_farmer_phones'),
               ('oan_farmer_land_summary'), ('oan_farmer_enumerator'), ('oan_farmer_documents')) e(section_id)
  WHERE NOT EXISTS (SELECT 1 FROM "public"."g2p_register_ui_tab_sections" t WHERE t.section_id = e.section_id);
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'OAN sections not on any register tab: %', missing;
  END IF;

  SELECT string_agg(section_id, ', ') INTO missing
  FROM (VALUES ('oan_farmer_personal_identification'), ('oan_farmer_socio_economic_and_health'),
               ('oan_farmer_membership_details'), ('oan_farmer_lands'), ('oan_farmer_livestock_intake'),
               ('oan_farmer_farm_inputs_intake'), ('oan_farmer_photo'),
               ('oan_household_information'), ('oan_farmer_location'), ('oan_farmer_crops_intake'),
               ('oan_farmer_phones'), ('oan_farmer_documents')) e(section_id)
  WHERE NOT EXISTS (SELECT 1 FROM "public"."g2p_intake_form_ui_tab_sections" t WHERE t.section_id = e.section_id);
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'OAN sections not on the intake form: %', missing;
  END IF;

  -- A section replaced by an OAN one must not show twice.
  SELECT string_agg(section_id, ', ') INTO missing
  FROM (SELECT section_id FROM "public"."g2p_register_ui_tab_sections"
        UNION ALL SELECT section_id FROM "public"."g2p_intake_form_ui_tab_sections"
                  WHERE section_id <> 'farmer_household_lookup_section_01') t
  WHERE section_id IN ('farmer_household_lookup_section_01', 'farmer_farmer_location_section_03',
                       'farmer_crop_crop_details_section_01', 'farmer_crop_crop_details_intake_section_01',
                       'household_household_household_information_section_01',
                       'bc882922-9008-4902-8f4f-98db0fa8f9ad');
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'Upstream sections still attached next to their OAN replacement: %', missing;
  END IF;

  -- The household is asked on the farmer's intake form (20_layout.sql).
  SELECT string_agg(section_id, ', ') INTO missing
  FROM (VALUES ('oan_household_information'), ('household_household_household_member_section_02')) e(section_id)
  WHERE NOT EXISTS (SELECT 1 FROM "public"."g2p_intake_form_ui_tab_sections" t
                    WHERE t.section_id = e.section_id AND t.tab_id = 'a1a4d25a-1cd4-4356-abac-72482721');
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'Household sections not on the farmer intake form: %', missing;
  END IF;

  -- A new household can be entered, so the household lookup is optional (10_sections.sql).
  IF EXISTS (SELECT 1 FROM "public"."g2p_register_sections" s,
                  jsonb_array_elements(s."section_ui_schema" #> '{panels,0,panels,0,widgets}') w
             WHERE s."section_id" = 'oan_farmer_household_lookup'
               AND w ->> 'widget-id' = 'household_lookup' AND (w ->> 'widget-required')::boolean IS TRUE) THEN
    RAISE EXCEPTION 'The household lookup on the farmer form is still required';
  END IF;
END $$;
