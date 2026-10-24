-- OAN sections: each one is an upstream section plus the OAN widgets, and the
-- intake photo section.
--
-- The image copies this folder to /seed/meta_data/zz-oan/, so it runs after the
-- farmer seed has upserted its own rows. Every OAN row is derived from the
-- upstream row on each run, so upstream changes to a section reach the OAN copy
-- the next time the seed runs. Upstream rows are never updated; 20_layout.sql
-- only detaches them from the tabs.

-- Sections that only gain widgets: the items are appended to the array at path.
WITH additions (upstream_section_id, oan_section_id, path, items) AS (
  VALUES
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

-- Personal identification, laid out as in the previous farmer registry: rows
-- stacked in one vertical panel. Upstream's row comes first, with its first,
-- middle and last name relabelled as the English first, father's and
-- grandfather's name. Then the primary language, the names in Amharic, and the
-- names in the primary language, which appear once a language is chosen and are
-- disabled when it is Amharic. The widget conditions apply rules in order and
-- the last show or hide wins, so "chosen and not Amharic" cannot be one rule.
-- The 1.2 widgets do not render panel titles, so each label names its language.
WITH relabel (widget_id, label) AS (
  VALUES ('first_name', 'first_name_eng'), ('middle_name', 'fathers_name_eng'), ('last_name', 'grandfathers_name_eng')
),
name_fields (ord, field, label) AS (
  VALUES (1, 'first_name', 'first_name'), (2, 'middle_name', 'fathers_name'), (3, 'last_name', 'grandfathers_name')
),
amharic AS (
  SELECT jsonb_agg(jsonb_build_object(
    'panel-id', 'oan_panel_amh_' || field, 'panel-orientation', 'vertical', 'widgets', jsonb_build_array(jsonb_build_object(
      'widget', 'text', 'widget-id', field || '_amh', 'widget-type', 'input', 'widget-label', label || '_amh',
      'widget-data-path', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.' || field || '_amh',
      'widget-data-validation', jsonb_build_object(
        'pattern', '^[\u1200-\u137F\u2D80-\u2DDF\uAB00-\uAB2F ]+$', 'maxLength', 100,
        'patternMessage', 'ethiopic_script_only'))))
    ORDER BY ord) AS panels
  FROM name_fields
),
other AS (
  SELECT jsonb_agg(jsonb_build_object(
    'panel-id', 'oan_panel_other_' || field, 'panel-orientation', 'vertical', 'widgets', jsonb_build_array(jsonb_build_object(
      'widget', 'text', 'widget-id', field || '_other', 'widget-type', 'input', 'widget-label', label || '_other',
      'widget-data-path', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.' || field || '_other',
      'widget-data-validation', jsonb_build_object('maxLength', 100),
      'widget-data-options', jsonb_build_object('actions', jsonb_build_array(
        jsonb_build_object('action', 'show', 'condition', jsonb_build_object(
          'field', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken', 'operator', 'notEmpty')),
        jsonb_build_object('action', 'disable', 'condition', jsonb_build_object(
          'field', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken', 'operator', 'equals', 'value', 'AMHARIC')))))))
    ORDER BY ord) AS panels
  FROM name_fields
),
rows AS (
  SELECT jsonb_build_array(
    jsonb_build_object('panel-id', 'oan_panel_language', 'panel-orientation', 'horizontal', 'panels', jsonb_build_array(
      jsonb_build_object('panel-id', 'oan_panel_language_spoken', 'panel-orientation', 'vertical', 'widgets', jsonb_build_array(
        '{"widget": "select", "widget-id": "language_spoken", "widget-type": "input", "widget-label": "primary_language",
          "widget-readonly": false, "widget-required": false,
          "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken",
          "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "LANGUAGE"},
                                 "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"}}'::jsonb)),
      -- Two empty columns keep the select one column wide, as in the rows below.
      jsonb_build_object('panel-id', 'oan_panel_language_spacer_1', 'panel-orientation', 'vertical', 'widgets', '[]'::jsonb),
      jsonb_build_object('panel-id', 'oan_panel_language_spacer_2', 'panel-orientation', 'vertical', 'widgets', '[]'::jsonb))),
    jsonb_build_object('panel-id', 'oan_panel_names_amh', 'panel-orientation', 'horizontal', 'panels', amharic.panels),
    jsonb_build_object('panel-id', 'oan_panel_names_other', 'panel-orientation', 'horizontal', 'panels', other.panels)) AS items
  FROM amharic, other
),
-- Upstream's panels with the name widgets relabelled; nothing else changes.
upstream_panels AS (
  SELECT u.section_id, jsonb_agg(
    CASE WHEN jsonb_typeof(p->'panels') = 'array' THEN jsonb_set(p, '{panels}', (
      SELECT jsonb_agg(CASE WHEN jsonb_typeof(c->'widgets') = 'array' THEN jsonb_set(c, '{widgets}', (
        SELECT COALESCE(jsonb_agg(w || COALESCE((SELECT jsonb_build_object('widget-label', r.label)
                                                 FROM relabel r WHERE r.widget_id = w->>'widget-id'), '{}'::jsonb)
                                  ORDER BY wi), '[]'::jsonb)
        FROM jsonb_array_elements(c->'widgets') WITH ORDINALITY x(w, wi))) ELSE c END ORDER BY ci)
      FROM jsonb_array_elements(p->'panels') WITH ORDINALITY y(c, ci))) ELSE p END
    ORDER BY pi) AS panels
  FROM "public"."g2p_register_sections" u,
       jsonb_array_elements(u.section_ui_schema->'panels') WITH ORDINALITY z(p, pi)
  WHERE u.section_id = 'farmer_farmer_personal_identification_section_01'
  GROUP BY u.section_id
)
INSERT INTO "public"."g2p_register_sections" (
  "register_id", "section_id", "section_register_id", "is_core_section", "section_mnemonic",
  "section_description", "documents_required", "no_of_verifications_required", "is_list",
  "section_weightage", "section_ui_schema", "cr_auto_approve_for_bene_portal",
  "cr_auto_approve_for_agent_portal", "cr_auto_approve_for_staff_portal", "cr_auto_approve_for_partner")
SELECT u.register_id, 'oan_farmer_personal_identification', u.section_register_id, u.is_core_section,
       'oan_' || u.section_mnemonic, u.section_description, u.documents_required,
       u.no_of_verifications_required, u.is_list, u.section_weightage,
       jsonb_set(u.section_ui_schema, '{panels}', jsonb_build_array(jsonb_build_object(
         'panel-id', 'oan_panel_personal_rows', 'panel-orientation', 'vertical',
         'panels', up.panels || rows.items))),
       u.cr_auto_approve_for_bene_portal, u.cr_auto_approve_for_agent_portal,
       u.cr_auto_approve_for_staff_portal, u.cr_auto_approve_for_partner
FROM "public"."g2p_register_sections" u
JOIN upstream_panels up ON up.section_id = u.section_id
CROSS JOIN rows
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

-- Farmer photo for the intake form. The register's detail view already has the
-- photo in upstream's header section (fr_farmer_header), with its own picker;
-- the intake form has no header, so without this a photo could only be added
-- after approval. This reuses the same header-section widget for its picker and
-- preview, with only the image paths: the widget reads and writes nothing for a
-- key without a path. On save the staff UI uploads the picked file and sets
-- record_image_document_id, the field the detail view's header shows. It is
-- attached to the intake form only (20_layout.sql), so the detail view does not
-- get a second picker for the same field.
INSERT INTO "public"."g2p_register_sections" (
  "register_id", "section_id", "section_register_id", "is_core_section", "section_mnemonic",
  "section_description", "documents_required", "no_of_verifications_required", "is_list",
  "section_weightage", "section_ui_schema", "cr_auto_approve_for_bene_portal",
  "cr_auto_approve_for_agent_portal", "cr_auto_approve_for_staff_portal", "cr_auto_approve_for_partner")
VALUES (
  'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd', 'oan_farmer_photo', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd', false,
  'oan_fr_farmer_photo', 'Farmer photo', false, 0, false, 0,
  '{"section-id": "farmer_photo", "section-title": "farmer_photo", "section-editable": true, "section-column-span": 3,
    "panels": [{"panel-id": "oan_panel_farmer_photo", "panel-orientation": "vertical", "widgets": [
      {"widget": "header-section", "widget-id": "farmer-photo", "widget-type": "group", "widget-label": "farmer_photo",
       "widget-readonly": false, "widget-required": false,
       "widget-data-path": {"image": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.record_image_document_id",
                            "imageUrl": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.record_image_url"},
       "widget-data-format": {"imageSize": 120}}]}]}'::jsonb,
  false, false, false, false)
ON CONFLICT ("section_id") DO UPDATE SET
  "register_id" = EXCLUDED."register_id", "section_register_id" = EXCLUDED."section_register_id",
  "section_mnemonic" = EXCLUDED."section_mnemonic", "section_description" = EXCLUDED."section_description",
  "section_ui_schema" = EXCLUDED."section_ui_schema";
