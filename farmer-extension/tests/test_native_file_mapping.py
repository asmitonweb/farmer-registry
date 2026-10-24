"""Domain contract tests; parsers are tested through the real platform worker."""
import openg2p_registry_celery_worker.main  # Initialize the platform extension alias.
import unittest
from openg2p_registry_farmer_extension.ingestion_pipeline.enricher_services.farmer_file_mapping import (
    RowError, row_to_submission, example_rows,
)


class NativeFileMappingTests(unittest.TestCase):
    def minimal(self, **extra):
        return dict(first_name='አበበ', father_first_name='Parent', **extra)

    def test_minimal_omits_optional_sections(self):
        result = row_to_submission(self.minimal())
        self.assertEqual(set(result), {'fr_farmer_personal_info', 'fr_farmer_household_lookup'})
        self.assertEqual(result['fr_farmer_personal_info'][0]['first_name'], 'አበበ')

    def test_full_parent_links_and_fresh_ids(self):
        result = row_to_submission(example_rows()[0])
        farmer = result['fr_farmer_personal_info'][0]
        household = result['fr_household_information'][0]
        self.assertEqual(farmer['link_internal_record_id'], household['internal_record_id'])
        self.assertEqual(result['fr_household_members'][0]['link_internal_record_id'], household['internal_record_id'])
        for section in ['intake_fr_farmer_land', 'intake_fr_farmer_crops', 'fr_farmer_livestocks',
                        'fr_farmer_membership', 'fr_farmer_farm_input', 'fr_farmer_phone_numbers']:
            self.assertEqual(result[section][0]['link_internal_record_id'], farmer['internal_record_id'])
            self.assertNotEqual(result[section][0]['internal_record_id'], farmer['internal_record_id'])
        again = row_to_submission(example_rows()[0])
        self.assertNotEqual(again['fr_farmer_personal_info'][0]['internal_record_id'], farmer['internal_record_id'])

    def test_identifier_text_and_coordinates(self):
        result = row_to_submission(self.minimal(national_fan='0012345678901234', phone_1='0911223344', latitude='-0.5', longitude='39.1234'))
        self.assertEqual(result['fr_farmer_reg_ids'][0]['value'], '0012345678901234')
        self.assertEqual(result['fr_farmer_phone_numbers'][0]['phone_number'], '0911223344')
        self.assertEqual(result['fr_farmer_location'][0]['latitude'], -0.5)

    def test_invalid_rows_are_rejected(self):
        for fields in [{'first_name':''}, {'gender':'INVALID'}, {'latitude':'NaN'}, {'longitude':'181'},
                       {'birth_date':'2025-02-30'}, {'birth_date_ec':'2016-13-07'},
                       {'livestock_1_type':'CATTLE','livestock_1_head_count':'1.5'},
                       {'crop_1_season':'MEHER'}, {'member_1_gender':'MALE'},
                       {'internal_record_id':'supplied-id'}, {'disabled':'maybe'}]:
            with self.subTest(fields=fields), self.assertRaises(RowError):
                row = self.minimal()
                row.update(fields)
                row_to_submission(row)

    def test_ethiopian_month_thirteen(self):
        result = row_to_submission(self.minimal(birth_date_ec='2015-13-05'))
        self.assertEqual(result['fr_farmer_birth_information'][0]['birth_date_ec'], '2015-13-05')


if __name__ == '__main__':
    unittest.main()
