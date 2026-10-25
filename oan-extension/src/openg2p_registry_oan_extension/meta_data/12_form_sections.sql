-- OAN's form sections, laid out as one row of three columns, the way upstream
-- lays out its own: personal identification, socio-economic and health,
-- membership, household information, location and documents.
--
-- form_layout says which widget goes in which column, in what order. A widget
-- with only a "widget-id" (plus any keys to change) is upstream's widget of that
-- id, taken from the upstream section on every run; a widget written out in
-- full is OAN's. 90_checks.sql fails the seed if an upstream id is not found.
-- column_span widens a column: the location map takes two.
--
-- Dates are upstream's date widget, entered in the Gregorian calendar; the
-- Ethiopian calendar twins are derived by the domain services.

-- Documents: six categories, each with the kind of document and up to
-- `slots` files. Only the identity document is required.
--
-- The staff UI saves each file under its file widget's label, and on reload
-- puts a document back at documents.<label>, one file per label. So a category
-- is `slots` upstream file widgets with the labels <category>_1, <category>_2
-- and so on; the first one is shown as OAN's documents widget
-- ("widget-variant": "oan-documents"), which lists the category's files and
-- adds a new one to the first free slot, and the others render nothing
-- ("oan-document-slot"). Upload, storage and reload stay upstream's. The slot
-- labels are keys, not translated, so they read back to the same field.
WITH doc_categories (category, col, ord, type_field, required, options) AS (
  VALUES
  ('identity_document', 1, 1, 'identity_document_type', true,
   '["FAYDA", "KEBELE_WOREDA_ID", "PASSPORT", "DRIVING_LICENCE", "KEBELE_CONFIRMATION_LETTER", "OTHER_GOVERNMENT_ID"]'::jsonb),
  ('bank_document', 1, 2, 'bank_document_type', false,
   '["BANK_PASSBOOK", "BANK_ACCOUNT_CONFIRMATION"]'),
  ('land_document', 2, 1, 'land_document_type', false,
   '["FIRST_LEVEL_CERTIFICATE", "SECOND_LEVEL_CERTIFICATE", "RENTAL_AGREEMENT", "SHARECROPPING_AGREEMENT",
     "LEASE_ALLOCATION_DOCUMENT", "INHERITANCE_TRANSFER_DOCUMENT", "LAND_OFFICE_CONFIRMATION"]'),
  ('representative_document', 2, 2, 'representative_document_type', false,
   '["POWER_OF_ATTORNEY", "GUARDIANSHIP_DOCUMENT", "REPRESENTATIVE_ID"]'),
  ('farmer_document', 3, 1, 'farmer_document_type', false,
   '["COOPERATIVE_MEMBERSHIP", "FARMER_GROUP_CONFIRMATION", "FARMER_CARD", "EXTENSION_OFFICE_CONFIRMATION"]'),
  ('other_document', 3, 2, 'other_document_purpose', false,
   '["IDENTITY_VERIFICATION", "ELIGIBILITY", "RECORD_CORRECTION", "OTHER_PURPOSE"]')
),
doc_settings (slots, accept, max_size) AS (
  VALUES (5, '.pdf,.jpg,.jpeg,.png', 5242880)
),
doc_widgets (col, ord, w) AS (
  -- The kind of document: a static list; the labels are translated keys.
  SELECT c.col, c.ord * 100, jsonb_build_object(
    'widget', 'select', 'widget-id', c.type_field, 'widget-type', 'input', 'widget-label', c.type_field,
    'widget-readonly', false, 'widget-required', c.required,
    'widget-data-path', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.' || c.type_field,
    'widget-data-source', jsonb_build_object('type', 'static', 'options',
      (SELECT jsonb_agg(jsonb_build_object('label', 'doc_' || lower(o), 'value', o) ORDER BY i)
       FROM jsonb_array_elements_text(c.options) WITH ORDINALITY x(o, i))))
  FROM doc_categories c
  UNION ALL
  -- "Other" also names the document.
  SELECT c.col, c.ord * 100 + 1, jsonb_build_object(
    'widget', 'text', 'widget-id', 'other_document_name', 'widget-type', 'input', 'widget-label', 'other_document_name',
    'widget-readonly', false, 'widget-required', false,
    'widget-data-path', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.other_document_name',
    'widget-data-validation', jsonb_build_object('maxLength', 100))
  FROM doc_categories c WHERE c.category = 'other_document'
  UNION ALL
  SELECT c.col, c.ord * 100 + 10 + n, jsonb_build_object(
    'widget', 'file', 'widget-id', c.category || '_' || n, 'widget-type', 'input',
    'widget-label', c.category || '_' || n, 'widget-required', c.required AND n = 1,
    'widget-variant', CASE WHEN n = 1 THEN 'oan-documents' ELSE 'oan-document-slot' END,
    'widget-data-path', 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.documents.' || c.category || '_' || n,
    'widget-data-options', jsonb_build_object('accept', d.accept, 'maxSize', d.max_size)
      || CASE WHEN n = 1 THEN jsonb_build_object(
           'title', c.category,
           'slots', (SELECT jsonb_agg('a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.documents.' || c.category || '_' || k ORDER BY k)
                     FROM generate_series(1, d.slots) k))
         ELSE '{}'::jsonb END)
  FROM doc_categories c CROSS JOIN doc_settings d CROSS JOIN generate_series(1, d.slots) n
),
form_layout (oan_section_id, upstream_section_id, col, ord, w) AS (
  VALUES
  -- Personal identification. Upstream's first, middle and last name are the
  -- English first, father's and grandfather's name. The names in the primary
  -- language appear once a language is chosen and are disabled when it is
  -- Amharic (the last show or hide rule wins, so "chosen and not Amharic" is
  -- two rules). The identifiers are attributes of the farmer: the Fayda FIN
  -- (upstream's foundational_id), the Fayda RID, the ODK Farmer ID and the Pula
  -- (Mavuno) ID.
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 1, 1,
   '{"widget-id": "first_name", "widget-label": "first_name_eng"}'::jsonb),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 1, 2,
   '{"widget-id": "middle_name", "widget-label": "fathers_name_eng"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 1, 3,
   '{"widget-id": "last_name", "widget-label": "grandfathers_name_eng"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 1, 4, '{"widget-id": "gender"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 1, 5, '{"widget-id": "birth_date"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 1, 6, '{"widget-id": "estimated_age"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 1,
   '{"widget": "text", "widget-id": "first_name_amh", "widget-type": "input", "widget-label": "first_name_amh",
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.first_name_amh",
     "widget-data-validation": {"pattern": "^[\u1200-\u137f\u2d80-\u2ddf\uab00-\uab2f ]+$", "maxLength": 100,
                                "patternMessage": "ethiopic_script_only"}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 2,
   '{"widget": "text", "widget-id": "middle_name_amh", "widget-type": "input", "widget-label": "fathers_name_amh",
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.middle_name_amh",
     "widget-data-validation": {"pattern": "^[\u1200-\u137f\u2d80-\u2ddf\uab00-\uab2f ]+$", "maxLength": 100,
                                "patternMessage": "ethiopic_script_only"}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 3,
   '{"widget": "text", "widget-id": "last_name_amh", "widget-type": "input", "widget-label": "grandfathers_name_amh",
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.last_name_amh",
     "widget-data-validation": {"pattern": "^[\u1200-\u137f\u2d80-\u2ddf\uab00-\uab2f ]+$", "maxLength": 100,
                                "patternMessage": "ethiopic_script_only"}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 4,
   '{"widget": "select", "widget-id": "language_spoken", "widget-type": "input", "widget-label": "primary_language",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken",
     "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "LANGUAGE"},
                            "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 5,
   '{"widget": "text", "widget-id": "first_name_other", "widget-type": "input", "widget-label": "first_name_other",
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.first_name_other", "widget-data-validation": {"maxLength": 100},
     "widget-data-options": {"actions": [
       {"action": "show", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken", "operator": "notEmpty"}},
       {"action": "disable", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken", "operator": "equals", "value": "AMHARIC"}}]}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 6,
   '{"widget": "text", "widget-id": "middle_name_other", "widget-type": "input", "widget-label": "fathers_name_other",
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.middle_name_other", "widget-data-validation": {"maxLength": 100},
     "widget-data-options": {"actions": [
       {"action": "show", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken", "operator": "notEmpty"}},
       {"action": "disable", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken", "operator": "equals", "value": "AMHARIC"}}]}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 2, 7,
   '{"widget": "text", "widget-id": "last_name_other", "widget-type": "input", "widget-label": "grandfathers_name_other",
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.last_name_other", "widget-data-validation": {"maxLength": 100},
     "widget-data-options": {"actions": [
       {"action": "show", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken", "operator": "notEmpty"}},
       {"action": "disable", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.language_spoken", "operator": "equals", "value": "AMHARIC"}}]}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 1, '{"widget-id": "marital_status"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 2, '{"widget-id": "education_level"}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 3,
   '{"widget": "boolean", "widget-id": "has_national_id", "widget-type": "input", "widget-label": "has_national_id",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.has_national_id",
     "widget-data-format": {"allowUnset": true, "booleanControlType": "radio", "booleanRepresentation": "yes-no"}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 4,
   '{"widget": "text", "widget-id": "foundational_id", "widget-type": "input", "widget-label": "fayda_fin",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.foundational_id",
     "widget-data-validation": {"pattern": "^[0-9]{12}$", "patternMessage": "fayda_fin_format"}}'),
  ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 5,
   '{"widget": "text", "widget-id": "rid", "widget-type": "input", "widget-label": "fayda_rid",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.rid",
     "widget-data-validation": {"pattern": "^[0-9]{29}$", "patternMessage": "fayda_rid_format"}}'),
   ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 6,
    '{"widget": "text", "widget-id": "odk_farmer_id", "widget-type": "input", "widget-label": "odk_farmer_id",
      "widget-readonly": false, "widget-required": false,
      "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.odk_farmer_id", "widget-data-validation": {"maxLength": 64}}'),
   ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 7,
    '{"widget": "text", "widget-id": "pula_id", "widget-type": "input", "widget-label": "pula_id",
      "widget-readonly": false, "widget-required": false,
      "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.pula_id", "widget-data-validation": {"maxLength": 64}}'),
   ('oan_farmer_personal_identification', 'farmer_farmer_personal_identification_section_01', 3, 8,
    '{"widget": "id-authentication", "widget-variant": "oan-intake", "widget-id": "farmer_intake_identity",
      "widget-type": "group", "widget-label": "identity_verification", "widget-readonly": true,
      "widget-data-path": {
        "contextId": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.intake_identity_context_id",
        "evidenceReference": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.identity_evidence_reference",
        "submissionId": "submission_id",
        "first_name": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.first_name",
        "middle_name": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.middle_name",
        "last_name": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.last_name",
        "birth_date": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.birth_date",
        "gender": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.gender",
        "foundational_id": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.foundational_id",
        "first_name_amh": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.first_name_amh",
        "middle_name_amh": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.middle_name_amh",
        "last_name_amh": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.last_name_amh"
      },
      "widget-auth-config": {
        "service": "registry", "providerId": "esignet", "providerName": "eSignet",
        "registerId": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd",
        "formId": "a1a4d25a-1cd4-4356-abac-8782382649",
        "startEndpoint": "intake-auth/start", "statusEndpoint": "intake-auth/status",
        "resetEndpoint": "intake-auth/reset", "mockVerifyEndpoint": "intake-auth/mock-verify",
        "mode": "mock", "mockPageUrl": "https://oan.closedroominc.qzz.io/mock-fayda/",
        "callbackOrigin": "http://farmer-registry.openg2p.localtest.me"
      }}'),

  -- Socio-economic and health: disability, income, then farming.
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 1, 1, '{"widget-id": "disabled"}'),
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 1, 2, '{"widget-id": "disability_type"}'),
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 1, 3, '{"widget-id": "disability_severity"}'),
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 2, 1, '{"widget-id": "source_of_income"}'),
  -- The other source of income, asked when the source is "Others".
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 2, 2,
   '{"widget": "text", "widget-id": "source_of_income_other", "widget-type": "input", "widget-label": "source_of_income_other",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.source_of_income_other",
     "widget-data-validation": {"maxLength": 100},
     "widget-data-options": {"actions": [
       {"action": "show", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.source_of_income", "value": "SOI_OTHERS", "operator": "equals"}},
       {"action": "require", "condition": {"field": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.source_of_income", "value": "SOI_OTHERS", "operator": "equals"}}]}}'),
  -- Productive Safety Net Programme beneficiary.
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 2, 3,
   '{"widget": "boolean", "widget-id": "is_psnp_user", "widget-type": "input", "widget-label": "is_psnp_user",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.is_psnp_user",
     "widget-data-format": {"allowUnset": true, "booleanControlType": "radio", "booleanRepresentation": "yes-no"}}'),
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 3, 1,
   '{"widget": "boolean", "widget-id": "is_farmer", "widget-type": "input", "widget-label": "is_farmer",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.is_farmer",
     "widget-data-format": {"allowUnset": true, "booleanControlType": "radio", "booleanRepresentation": "yes-no"}}'),
  ('oan_farmer_socio_economic_and_health', 'farmer_farmer_socio_economic_and_health_section_04', 3, 2,
   '{"widget": "select", "widget-id": "farming_type", "widget-type": "input", "widget-label": "farming_type",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.farming_type",
     "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "FARMING_TYPE"},
                            "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"}}'),

  -- Membership: one column per kind of membership, and the cluster's focal
  -- commodity for cluster members.
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 1, 1, '{"widget-id": "is_primary_cooperative_member"}'),
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 1, 2, '{"widget-id": "primary_cooperative_name"}'),
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 2, 1, '{"widget-id": "is_cooperative_union_member"}'),
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 2, 2, '{"widget-id": "cooperative_union_name"}'),
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 3, 1, '{"widget-id": "is_farmer_cluster_member"}'),
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 3, 2, '{"widget-id": "farmer_cluster_role"}'),
  ('oan_farmer_membership_details', 'farmer_membership_membership_details_01', 3, 3,
   '{"widget": "select", "widget-id": "primary_commodity", "widget-type": "input", "widget-label": "primary_commodity",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "495f251c-83a5-4025-a307-1925712c9d0b.primary_commodity",
     "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "CROP_COMMODITY"},
                            "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"},
     "widget-data-options": {"actions": [
       {"action": "show", "condition": {"field": "495f251c-83a5-4025-a307-1925712c9d0b.is_farmer_cluster_member", "value": true, "operator": "equals"}}]}}'),

  -- Household information: its size, its make-up, then who else is in it.
  ('oan_household_information', 'household_household_household_information_section_01', 1, 1, '{"widget-id": "size_of_group"}'),
  ('oan_household_information', 'household_household_household_information_section_01', 1, 2, '{"widget-id": "number_of_children"}'),
  ('oan_household_information', 'household_household_household_information_section_01', 2, 1, '{"widget-id": "number_of_male_members"}'),
  ('oan_household_information', 'household_household_household_information_section_01', 2, 2, '{"widget-id": "number_of_female_members"}'),
  ('oan_household_information', 'household_household_household_information_section_01', 2, 3, '{"widget-id": "number_of_elderly_members"}'),
  ('oan_household_information', 'household_household_household_information_section_01', 3, 1, '{"widget-id": "other_land_owner"}'),
  ('oan_household_information', 'household_household_household_information_section_01', 3, 2,
   '{"widget": "boolean", "widget-id": "other_farmer_in_household", "widget-type": "input", "widget-label": "other_farmer_in_household",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "9055ab43-c85d-4833-bd00-ca657bb72644.other_farmer_in_household",
     "widget-data-format": {"allowUnset": true, "booleanControlType": "radio", "booleanRepresentation": "yes-no"}}'),
  ('oan_household_information', 'household_household_household_information_section_01', 3, 3,
   '{"widget": "boolean", "widget-id": "father_included", "widget-type": "input", "widget-label": "father_included",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "9055ab43-c85d-4833-bd00-ca657bb72644.father_included",
     "widget-data-format": {"allowUnset": true, "booleanControlType": "radio", "booleanRepresentation": "yes-no"}}'),
  ('oan_household_information', 'household_household_household_information_section_01', 3, 4,
   '{"widget": "boolean", "widget-id": "mother_included", "widget-type": "input", "widget-label": "mother_included",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "9055ab43-c85d-4833-bd00-ca657bb72644.mother_included",
     "widget-data-format": {"allowUnset": true, "booleanControlType": "radio", "booleanRepresentation": "yes-no"}}'),

  -- Location: the map across the first two columns, the location and the
  -- address in the third. The map pins where the farmer lives: OpenStreetMap
  -- tiles kept to Ethiopia ("bounds"), click or drag to place the pin, or use
  -- the device's position. The pin fills the location hierarchy from Master
  -- Data, so every OAN registry and dashboard uses the same map and ids: Master
  -- Data serves the woreda polygons it seeds from the country pack (ETH-OAN's
  -- boundaries/, OCHA COD-AB), the woreda under the pin gives its P-code, and
  -- its region and zone are read from Master Data. The kebele has no polygons,
  -- so it is chosen from the woreda's list; where a woreda has no polygon (new
  -- since 2021) the location is chosen from the lists. Latitude and longitude
  -- are the pin's; the altitude is the device's when it reports one, otherwise
  -- the ground elevation at the pin from "elevationUrl". That sends the pin's
  -- coordinates to the elevation service, so remove "elevationUrl" where that
  -- is not acceptable, and the altitude stays as typed. Tile and elevation hosts
  -- must be allowed by the staff UI's CSP (CSP_SRC_IMG, CSP_SRC_CONNECT).
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 1, '{"widget-id": "farmer_geo_hierarchy"}'),
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 2, '{"widget-id": "address_line_1"}'),
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 3, '{"widget-id": "address_line_2"}'),
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 4, '{"widget-id": "postal_code"}'),
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 5, '{"widget-id": "country_code"}'),
  -- A second, local or community language.
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 6,
   '{"widget": "select", "widget-id": "local_language", "widget-type": "input", "widget-label": "local_language",
     "widget-readonly": false, "widget-required": false,
     "widget-data-path": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.local_language",
     "widget-data-source": {"type": "api", "method": "POST", "params": {"attribute_id": "LANGUAGE"},
                            "service": "attributes", "endpoint": "values", "labelKey": "value_display", "valueKey": "value_code"}}'),
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 2, 7, '{"widget-id": "plus_code"}'),
  ('oan_farmer_location', 'farmer_farmer_location_section_03', 1, 1,
   '{"widget": "oan-geo-point", "widget-id": "farmer_geo_point", "widget-type": "input",
     "widget-label": "farmer_location", "widget-readonly": false, "widget-required": false,
     "widget-data-path": {"latitude": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.latitude",
                          "longitude": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.longitude",
                          "altitude": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.altitude",
                          "hierarchy": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.geo_code_hierarchy_json",
                          "location": "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd.geo_lowest_level_value_id"},
     "widget-data-format": {"bounds": [[3.3, 32.9], [15.0, 48.1]], "minZoom": 5,
                            "boundaries": {"url": "/api/master-data/geo-boundary?level=woreda",
                                           "geoSource": {"service": "master-data", "method": "POST",
                                                         "levelsEndpoint": "get-all-g2p-geo-levels",
                                                         "valuesEndpoint": "geo-level-values"}},
                            "tileUrl": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                            "attribution": "\u00a9 OpenStreetMap contributors; boundaries OCHA COD-AB",
                            "center": [9.145, 40.4897], "zoom": 6, "pinZoom": 15, "maxZoom": 19, "height": 420,
                            "elevationUrl": "https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"}}')

  -- Documents: upstream's section, with the categories above as its widgets.
  UNION ALL
  SELECT 'oan_farmer_documents', 'bc882922-9008-4902-8f4f-98db0fa8f9ad', col, ord, w FROM doc_widgets
),
column_span (oan_section_id, col, span) AS (
  VALUES ('oan_farmer_location', 1, 2)
),
placed AS (
  SELECT l.oan_section_id, l.col, l.ord,
         COALESCE(jsonb_path_query_first(u.section_ui_schema, '$.**.widgets[*] ? (@."widget-id" == $id)',
                                         jsonb_build_object('id', l.w->>'widget-id')), '{}'::jsonb) || l.w AS w
  FROM form_layout l
  JOIN "public"."g2p_register_sections" u ON u.section_id = l.upstream_section_id
),
columns AS (
  SELECT p.oan_section_id, p.col,
         jsonb_build_object('panel-id', p.oan_section_id || '_col_' || p.col, 'panel-orientation', 'vertical',
                            'widgets', jsonb_agg(p.w ORDER BY p.ord))
         || COALESCE((SELECT jsonb_build_object('panel-column-span', s.span) FROM column_span s
                      WHERE s.oan_section_id = p.oan_section_id AND s.col = p.col), '{}'::jsonb) AS panel
  FROM placed p
  GROUP BY p.oan_section_id, p.col
),
panels AS (
  SELECT oan_section_id,
         jsonb_build_array(jsonb_build_object('panel-id', oan_section_id || '_row', 'panel-orientation', 'horizontal',
                                              'panels', jsonb_agg(panel ORDER BY col))) AS panels
  FROM columns
  GROUP BY oan_section_id
)
INSERT INTO "public"."g2p_register_sections" (
  "register_id", "section_id", "section_register_id", "is_core_section", "section_mnemonic",
  "section_description", "documents_required", "no_of_verifications_required", "is_list",
  "section_weightage", "section_ui_schema", "cr_auto_approve_for_bene_portal",
  "cr_auto_approve_for_agent_portal", "cr_auto_approve_for_staff_portal", "cr_auto_approve_for_partner")
SELECT u.register_id, d.oan_section_id, u.section_register_id, u.is_core_section, 'oan_' || u.section_mnemonic,
       u.section_description, u.documents_required, u.no_of_verifications_required, u.is_list, u.section_weightage,
       jsonb_set(u.section_ui_schema, '{panels}', p.panels),
       u.cr_auto_approve_for_bene_portal, u.cr_auto_approve_for_agent_portal,
       u.cr_auto_approve_for_staff_portal, u.cr_auto_approve_for_partner
FROM (SELECT DISTINCT oan_section_id, upstream_section_id FROM form_layout) d
JOIN "public"."g2p_register_sections" u ON u.section_id = d.upstream_section_id
JOIN panels p ON p.oan_section_id = d.oan_section_id
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
