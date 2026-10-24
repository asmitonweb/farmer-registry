-- Put the OAN sections where the upstream ones were, on the register tabs and
-- the intake form, then detach the upstream sections from those places.
--
-- Each OAN attachment copies the tab and order of the upstream one it replaces.
-- The upstream rows are removed by explicit id, never by NOT IN, so a section
-- upstream adds later is left alone. The farmer seed re-inserts them on every
-- run, and this file removes them again right after.

WITH replaced (upstream_section_id, oan_section_id) AS (
  VALUES ('farmer_farmer_personal_identification_section_01', 'oan_farmer_personal_identification'),
         ('farmer_farmer_socio_economic_and_health_section_04', 'oan_farmer_socio_economic_and_health'),
         ('farmer_membership_membership_details_01', 'oan_farmer_membership_details'),
         ('farmer_farm_farm_details_section_01', 'oan_farmer_lands'),
         ('farmer_livestock_livestock_details_section_01', 'oan_farmer_livestock'),
         ('farmer_livestock_livestock_details_intake_section_01', 'oan_farmer_livestock_intake'),
         ('farmer_farm_input_farm_input_details_section_01', 'oan_farmer_farm_inputs'),
         ('farmer_farm_input_farm_input_details_intake_section_01', 'oan_farmer_farm_inputs_intake')
)
INSERT INTO "public"."g2p_register_ui_tab_sections" ("tab_section_id", "register_id", "tab_id", "section_id", "section_order")
SELECT 'oan_' || t.tab_section_id, t.register_id, t.tab_id, r.oan_section_id, t.section_order
FROM "public"."g2p_register_ui_tab_sections" t
JOIN replaced r ON r.upstream_section_id = t.section_id
JOIN "public"."g2p_register_sections" s ON s.section_id = r.oan_section_id
WHERE t.register_id = 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd'
ON CONFLICT ("tab_section_id") DO UPDATE SET
  "register_id" = EXCLUDED."register_id", "tab_id" = EXCLUDED."tab_id",
  "section_id" = EXCLUDED."section_id", "section_order" = EXCLUDED."section_order";

WITH replaced (upstream_section_id, oan_section_id) AS (
  VALUES ('farmer_farmer_personal_identification_section_01', 'oan_farmer_personal_identification'),
         ('farmer_farmer_socio_economic_and_health_section_04', 'oan_farmer_socio_economic_and_health'),
         ('farmer_membership_membership_details_01', 'oan_farmer_membership_details'),
         ('farmer_farm_farm_details_section_01', 'oan_farmer_lands'),
         ('farmer_livestock_livestock_details_intake_section_01', 'oan_farmer_livestock_intake'),
         ('farmer_farm_input_farm_input_details_intake_section_01', 'oan_farmer_farm_inputs_intake')
)
INSERT INTO "public"."g2p_intake_form_ui_tab_sections" ("tab_section_id", "tab_id", "section_id", "section_order")
SELECT 'oan_' || t.tab_section_id, t.tab_id, r.oan_section_id, t.section_order
FROM "public"."g2p_intake_form_ui_tab_sections" t
JOIN replaced r ON r.upstream_section_id = t.section_id
JOIN "public"."g2p_register_sections" s ON s.section_id = r.oan_section_id
WHERE t.tab_id = 'a1a4d25a-1cd4-4356-abac-72482721'
ON CONFLICT ("tab_section_id") DO UPDATE SET
  "tab_id" = EXCLUDED."tab_id", "section_id" = EXCLUDED."section_id", "section_order" = EXCLUDED."section_order";

-- Detach upstream, only where the OAN replacement is attached.
DELETE FROM "public"."g2p_register_ui_tab_sections"
WHERE "tab_section_id" IN (
  'a6ab60bd-07be-4237-aefd-7f6e3c1ced4f',  -- farmer tab: personal identification
  '9a1573a0-6507-47b6-a717-a007435d2c76',  -- farmer tab: socio-economic and health
  '14691011-f41c-4010-be96-af39207b5fc3',  -- membership tab
  '41a866b7-d301-46e3-8375-17ebb9f0059d',  -- lands tab
  'b46853a4-ba5b-4378-ae62-9a274448ac65',  -- livestock tab
  '7c46c33d-9519-4027-b071-3a7e8822ae87'   -- farm inputs tab
)
AND EXISTS (SELECT 1 FROM "public"."g2p_register_ui_tab_sections" o
            WHERE o."tab_section_id" = 'oan_' || "g2p_register_ui_tab_sections"."tab_section_id");

DELETE FROM "public"."g2p_intake_form_ui_tab_sections"
WHERE "tab_section_id" IN (
  'tab_section_3',                         -- personal identification
  'tab_section_4',                         -- socio-economic and health
  'tab_section_6',                         -- lands
  'bb3542b4-2f6b-443e-b9b5-65ce0b0a6eb8',  -- farm inputs
  '46392474-53a0-4737-ab8e-c942efc73153',  -- livestock
  'tab_section_9'                          -- membership
)
AND EXISTS (SELECT 1 FROM "public"."g2p_intake_form_ui_tab_sections" o
            WHERE o."tab_section_id" = 'oan_' || "g2p_intake_form_ui_tab_sections"."tab_section_id");

-- The photo section, on the intake form only, right after personal
-- identification (see 10_sections.sql for why not on the register tabs).
INSERT INTO "public"."g2p_intake_form_ui_tab_sections" ("tab_section_id", "tab_id", "section_id", "section_order")
SELECT 'oan_farmer_photo_intake', t.tab_id, 'oan_farmer_photo', t.section_order + 5
FROM "public"."g2p_intake_form_ui_tab_sections" t
WHERE t.tab_section_id = 'oan_tab_section_3'
ON CONFLICT ("tab_section_id") DO UPDATE SET
  "tab_id" = EXCLUDED."tab_id", "section_id" = EXCLUDED."section_id", "section_order" = EXCLUDED."section_order";
