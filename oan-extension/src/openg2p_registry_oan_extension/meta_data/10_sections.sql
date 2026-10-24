-- OAN sections: each one is an upstream section plus the OAN widgets.
--
-- The image copies this folder to /seed/meta_data/zz-oan/, so it runs after the
-- farmer seed has upserted its own rows. Every OAN row is derived from the
-- upstream row on each run, so upstream changes to a section reach the OAN copy
-- the next time the seed runs. Upstream rows are never updated; 20_layout.sql
-- only detaches them from the tabs.

WITH additions (upstream_section_id, oan_section_id, path, items) AS (
  VALUES
  -- Personal identification: the names in Ethiopic and Latin script, and the
  -- father's names, as a second row under upstream's three columns.
  ('farmer_farmer_personal_identification_section_01',
   'oan_farmer_personal_identification',
   '{panels}'::text[],
   '[{"panel-id": "oan_panel_other_names", "panel-orientation": "horizontal", "panels": [
      {"panel-id": "oan_panel_names_amh", "panel-title": "names_in_amharic", "panel-orientation": "vertical", "widgets": [
        {"widget": "text", "widget-id": "first_name_amh", "widget-type": "input", "widget-label": "first_name_amh",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.first_name_amh",
         "widget-data-validation": {"pattern": "^[\\u1200-\\u137F\\u2D80-\\u2DDF\\uAB00-\\uAB2F ]+$", "maxLength": 100, "patternMessage": "ethiopic_script_only"}},
        {"widget": "text", "widget-id": "middle_name_amh", "widget-type": "input", "widget-label": "middle_name_amh",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.middle_name_amh",
         "widget-data-validation": {"pattern": "^[\\u1200-\\u137F\\u2D80-\\u2DDF\\uAB00-\\uAB2F ]+$", "maxLength": 100, "patternMessage": "ethiopic_script_only"}},
        {"widget": "text", "widget-id": "last_name_amh", "widget-type": "input", "widget-label": "last_name_amh",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.last_name_amh",
         "widget-data-validation": {"pattern": "^[\\u1200-\\u137F\\u2D80-\\u2DDF\\uAB00-\\uAB2F ]+$", "maxLength": 100, "patternMessage": "ethiopic_script_only"}}]},
      {"panel-id": "oan_panel_names_om", "panel-title": "names_in_afaan_oromo", "panel-orientation": "vertical", "widgets": [
        {"widget": "text", "widget-id": "first_name_om", "widget-type": "input", "widget-label": "first_name_om",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.first_name_om",
         "widget-data-validation": {"pattern": "^[A-Za-z'' -]+$", "maxLength": 100, "patternMessage": "latin_script_only"}},
        {"widget": "text", "widget-id": "middle_name_om", "widget-type": "input", "widget-label": "middle_name_om",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.middle_name_om",
         "widget-data-validation": {"pattern": "^[A-Za-z'' -]+$", "maxLength": 100, "patternMessage": "latin_script_only"}},
        {"widget": "text", "widget-id": "last_name_om", "widget-type": "input", "widget-label": "last_name_om",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.last_name_om",
         "widget-data-validation": {"pattern": "^[A-Za-z'' -]+$", "maxLength": 100, "patternMessage": "latin_script_only"}}]},
      {"panel-id": "oan_panel_father_name", "panel-title": "father_name", "panel-orientation": "vertical", "widgets": [
        {"widget": "text", "widget-id": "father_first_name", "widget-type": "input", "widget-label": "father_first_name",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.father_first_name",
         "widget-data-validation": {"maxLength": 100}},
        {"widget": "text", "widget-id": "father_middle_name", "widget-type": "input", "widget-label": "father_middle_name",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.father_middle_name",
         "widget-data-validation": {"maxLength": 100}},
        {"widget": "text", "widget-id": "father_last_name", "widget-type": "input", "widget-label": "father_last_name",
         "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.father_last_name",
         "widget-data-validation": {"maxLength": 100}}]}]}]'::jsonb),

  -- Socio-economic: Productive Safety Net Programme beneficiary.
  ('farmer_farmer_socio_economic_and_health_section_04',
   'oan_farmer_socio_economic_and_health',
   '{panels,0,panels,1,widgets}'::text[],
   '[{"widget": "select", "widget-id": "is_psnp_user", "widget-type": "input", "widget-label": "is_psnp_user",
      "widget-readonly": false, "widget-required": false,
      "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.is_psnp_user",
      "widget-data-source": {"type": "static", "options": [{"label": "YES", "value": true}, {"label": "NO", "value": false}]}}]'::jsonb),

  -- Membership: the cluster's focal commodity, shown for cluster members.
  ('farmer_membership_membership_details_01',
   'oan_farmer_membership_details',
   '{panels,0,panels,2,widgets}'::text[],
   '[{"widget": "select", "widget-id": "primary_commodity", "widget-type": "input", "widget-label": "primary_commodity",
      "widget-readonly": false, "widget-required": false,
      "widget-data-path": "495f251c-83a5-4025-a307-1925712c9d0b.primary_commodity",
      "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "CROP_COMMODITY"},
                             "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"},
      "widget-data-options": {"actions": [
        {"action": "show", "condition": {"field": "495f251c-83a5-4025-a307-1925712c9d0b.is_farmer_cluster_member", "value": true, "operator": "equals"}}]}}]'::jsonb),

  -- Lands table (the register and the intake form share this section).
  ('farmer_farm_farm_details_section_01',
   'oan_farmer_lands',
   '{panels,0,panels,0,widgets,0,widget-data-columns}'::text[],
   '[{"widget": "text", "column-key": "land_id", "widget-type": "input", "widget-label": "land_id",
      "widget-readonly": false, "widget-data-path": "land_id", "widget-data-validation": {"maxLength": 50}},
     {"widget": "text", "column-key": "remark", "widget-type": "input", "widget-label": "remark",
      "widget-readonly": false, "widget-data-path": "remark", "widget-data-validation": {"maxLength": 500}}]'::jsonb),

  -- Livestock tables.
  ('farmer_livestock_livestock_details_section_01', 'oan_farmer_livestock', '{panels,0,panels,0,widgets,0,widget-data-columns}'::text[], NULL),
  ('farmer_livestock_livestock_details_intake_section_01', 'oan_farmer_livestock_intake', '{panels,0,panels,0,widgets,0,widget-data-columns}'::text[], NULL),

  -- Farm input tables.
  ('farmer_farm_input_farm_input_details_section_01', 'oan_farmer_farm_inputs', '{panels,0,panels,0,widgets,0,widget-data-columns}'::text[], NULL),
  ('farmer_farm_input_farm_input_details_intake_section_01', 'oan_farmer_farm_inputs_intake', '{panels,0,panels,0,widgets,0,widget-data-columns}'::text[], NULL)
),
shared_columns (oan_section_id, items) AS (
  SELECT oan_section_id, cols FROM (VALUES ('oan_farmer_livestock'), ('oan_farmer_livestock_intake')) s(oan_section_id),
  LATERAL (SELECT '[{"widget": "select", "column-key": "gender", "widget-type": "input", "widget-label": "gender",
      "widget-readonly": false, "widget-data-path": "gender",
      "widget-data-source": {"type": "static", "options": [{"label": "MALE", "value": "MALE"}, {"label": "FEMALE", "value": "FEMALE"}]}},
     {"widget": "select", "column-key": "body_condition", "widget-type": "input", "widget-label": "body_condition",
      "widget-readonly": false, "widget-data-path": "body_condition",
      "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "LIVESTOCK_BODY_CONDITION"},
                             "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"}},
     {"widget": "select", "column-key": "production_type", "widget-type": "input", "widget-label": "production_type",
      "widget-readonly": false, "widget-data-path": "production_type",
      "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "LIVESTOCK_PRODUCTION_TYPE"},
                             "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"}}]'::jsonb) c(cols)
  UNION ALL
  -- Each amount shows only when the matching "used" answer is yes.
  SELECT oan_section_id, (
    SELECT jsonb_agg(jsonb_build_object(
      'widget', 'number', 'column-key', amount, 'widget-type', 'input', 'widget-label', amount,
      'widget-readonly', false, 'widget-data-path', amount,
      'widget-data-format', jsonb_build_object('allowSigned', false, 'numericType', 'decimal', 'decimalPlaces', 3,
                                               'decimalSeparator', '.', 'thousandSeparator', ','),
      'widget-data-validation', jsonb_build_object('min', 0),
      'widget-data-options', jsonb_build_object('actions', jsonb_build_array(
        jsonb_build_object('action', 'show', 'condition', jsonb_build_object('field', used, 'value', true, 'operator', 'equals'))))
    ) ORDER BY ord)
    FROM (VALUES (1, 'amount_fertilizer_utilized', 'fertilizer_use'),
                 (2, 'amount_pesticide_utilized', 'pesticide_use'),
                 (3, 'amount_insecticide_utilized', 'insecticide_use'),
                 (4, 'amount_improved_seed_utilized', 'improved_seed_use')) a(ord, amount, used))
  FROM (VALUES ('oan_farmer_farm_inputs'), ('oan_farmer_farm_inputs_intake')) s(oan_section_id)
)
INSERT INTO "public"."g2p_register_sections" (
  "register_id", "section_id", "section_register_id", "is_core_section", "section_mnemonic",
  "section_description", "documents_required", "no_of_verifications_required", "is_list",
  "section_weightage", "section_ui_schema", "cr_auto_approve_for_bene_portal",
  "cr_auto_approve_for_agent_portal", "cr_auto_approve_for_staff_portal", "cr_auto_approve_for_partner")
SELECT u.register_id, a.oan_section_id, u.section_register_id, u.is_core_section, 'oan_' || u.section_mnemonic,
       u.section_description, u.documents_required, u.no_of_verifications_required, u.is_list,
       u.section_weightage,
       jsonb_set(u.section_ui_schema, a.path,
                 (u.section_ui_schema #> a.path) || COALESCE(a.items, s.items)),
       u.cr_auto_approve_for_bene_portal, u.cr_auto_approve_for_agent_portal,
       u.cr_auto_approve_for_staff_portal, u.cr_auto_approve_for_partner
FROM additions a
JOIN "public"."g2p_register_sections" u ON u.section_id = a.upstream_section_id
LEFT JOIN shared_columns s ON s.oan_section_id = a.oan_section_id
WHERE jsonb_typeof(u.section_ui_schema #> a.path) = 'array'
ON CONFLICT ("section_id") DO UPDATE SET
  "register_id" = EXCLUDED."register_id", "section_register_id" = EXCLUDED."section_register_id",
  "is_core_section" = EXCLUDED."is_core_section", "section_mnemonic" = EXCLUDED."section_mnemonic",
  "section_description" = EXCLUDED."section_description", "documents_required" = EXCLUDED."documents_required",
  "no_of_verifications_required" = EXCLUDED."no_of_verifications_required", "is_list" = EXCLUDED."is_list",
  "section_weightage" = EXCLUDED."section_weightage", "section_ui_schema" = EXCLUDED."section_ui_schema",
  "cr_auto_approve_for_bene_portal" = EXCLUDED."cr_auto_approve_for_bene_portal",
  "cr_auto_approve_for_agent_portal" = EXCLUDED."cr_auto_approve_for_agent_portal",
  "cr_auto_approve_for_staff_portal" = EXCLUDED."cr_auto_approve_for_staff_portal",
  "cr_auto_approve_for_partner" = EXCLUDED."cr_auto_approve_for_partner";
