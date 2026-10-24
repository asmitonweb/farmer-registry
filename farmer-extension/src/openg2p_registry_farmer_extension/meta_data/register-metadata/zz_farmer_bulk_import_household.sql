-- Keep one household parent section before linked person sections. Existing
-- installations may already carry this section; do not add a duplicate.
INSERT INTO public.g2p_intake_form_ui_tab_sections
    (tab_section_id, tab_id, section_id, section_order)
SELECT 'farmer_native_household_information',
       'a1a4d25a-1cd4-4356-abac-72482721',
       'farmer_household_household_information_section_01', 12
WHERE NOT EXISTS (SELECT 1 FROM public.g2p_intake_form_ui_tab_sections
    WHERE tab_id='a1a4d25a-1cd4-4356-abac-72482721'
      AND section_id='farmer_household_household_information_section_01')
ON CONFLICT DO NOTHING;
