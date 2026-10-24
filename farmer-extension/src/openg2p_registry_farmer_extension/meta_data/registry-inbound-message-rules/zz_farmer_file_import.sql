-- Native staff CSV/XLSX import. Additive, stable IDs; preserve administrator edits.
INSERT INTO public.data_models (data_model_id,data_model_mnemonic,pattern_for_data_model,response_template_document_id,is_active)
VALUES ('FARMER_FILE_IMPORT_MODEL','FARMER_FILE_IMPORT_MODEL','$.headers.sender_id=>^.*$',
NULL,true) ON CONFLICT DO NOTHING;
INSERT INTO public.incoming_model_key_paths
(key_path_id,data_model_id,key_path_for_message_id,key_path_for_sender,key_path_for_signature,key_path_for_signature_payload,is_list,key_path_for_list_elements)
VALUES ('farmer_file_import_key_path','FARMER_FILE_IMPORT_MODEL','$.headers.message_id','$.headers.sender_id','$.headers.signature','$.body',false,'') ON CONFLICT DO NOTHING;
INSERT INTO public.incoming_model_semantic_patterns
(semantic_pattern_id,data_model_id,register_id,intake_form_id,section_id,pattern_for_register,pattern_for_intake_form,pattern_for_section,key_path_for_business_payload,raw_payload_enricher_class)
VALUES ('farmer_file_import_semantic','FARMER_FILE_IMPORT_MODEL','a1a4d25a-1cd4-4356-abac-985a0b3c6bcd','a1a4d25a-1cd4-4356-abac-8782382649',NULL,NULL,'$.headers.sender_id=>^.*$',NULL,'$.body','G2PFarmerFileImportEnricherService') ON CONFLICT DO NOTHING;
INSERT INTO public.g2p_registry_documents (document_id,document_store_id,bucket,source_filename,created_by,created_at)
VALUES ('farmer-file-import-template','farmer_file_import.json.j2','templates','farmer_file_import.json.j2','seeder',CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING;
INSERT INTO public.incoming_templates (template_id,register_id,data_model_id,template_document_id,jsonld_expansion_required,created_at)
VALUES ('FARMER-FILE-IMPORT-TEMPLATE','a1a4d25a-1cd4-4356-abac-985a0b3c6bcd','FARMER_FILE_IMPORT_MODEL','farmer-file-import-template',false,CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING;
INSERT INTO public.g2p_registry_import_file_configurations
(import_file_configuration_id,register_id,form_id,data_model_id,import_file_template_mnemonic,import_file_template_description)
VALUES ('farmer-native-file-import','a1a4d25a-1cd4-4356-abac-985a0b3c6bcd','a1a4d25a-1cd4-4356-abac-8782382649','FARMER_FILE_IMPORT_MODEL','Farmer CSV / XLSX','Create farmer intakes using the documented farmer column template') ON CONFLICT DO NOTHING;
INSERT INTO public.g2p_input_mechanisms (mechanism_id,register_id,mechanism_type,display_key)
SELECT 'farmer-native-file-mechanism','a1a4d25a-1cd4-4356-abac-985a0b3c6bcd','IMPORT_FILE','Import File'
WHERE NOT EXISTS (SELECT 1 FROM public.g2p_input_mechanisms WHERE register_id='a1a4d25a-1cd4-4356-abac-985a0b3c6bcd' AND mechanism_type='IMPORT_FILE') ON CONFLICT DO NOTHING;
INSERT INTO public.g2p_input_mechanisms (mechanism_id,register_id,mechanism_type,display_key)
SELECT 'farmer-native-manual-mechanism','a1a4d25a-1cd4-4356-abac-985a0b3c6bcd','INTAKE_FORM','Intake Form'
WHERE NOT EXISTS (SELECT 1 FROM public.g2p_input_mechanisms WHERE register_id='a1a4d25a-1cd4-4356-abac-985a0b3c6bcd' AND mechanism_type='INTAKE_FORM') ON CONFLICT DO NOTHING;
