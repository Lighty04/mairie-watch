import unittest
from unittest.mock import MagicMock, patch
from datetime import date
from app.quotas import (
    get_remaining_summaries, 
    can_generate_summary, 
    record_summary_usage, 
    get_today_date_str
)
from app.models import SummaryUsage

class TestQuotas(unittest.TestCase):
    
    def setUp(self):
        # Mock the DB session object
        self.mock_db = MagicMock()
        self.user_id_free = 1
        self.user_id_pro = 2
        self.today_str = get_today_date_str()

    # --- Test get_remaining_summaries ---
    
    def test_pro_user_unlimited(self):
        # Pro user should always be -1 (unlimited)
        remaining = get_remaining_summaries(self.user_id_pro, "Pro", self.mock_db)
        self.assertEqual(remaining, -1)

    def test_free_user_no_usage(self):
        # Free user with no usage should have 3 remaining
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        remaining = get_remaining_summaries(self.user_id_free, "Free", self.mock_db)
        self.assertEqual(remaining, 3)

    def test_free_user_partial_usage(self):
        # Free user with 1 usage should have 2 remaining
        mock_usage = SummaryUsage(user_id=self.user_id_free, date=self.today_str, count=1)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_usage
        remaining = get_remaining_summaries(self.user_id_free, "Free", self.mock_db)
        self.assertEqual(remaining, 2)

    def test_free_user_full_usage(self):
        # Free user with 3 usage should have 0 remaining
        mock_usage = SummaryUsage(user_id=self.user_id_free, date=self.today_str, count=3)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_usage
        remaining = get_remaining_summaries(self.user_id_free, "Free", self.mock_db)
        self.assertEqual(remaining, 0)

    # --- Test can_generate_summary ---

    def test_can_generate_summary_pro(self):
        self.assertTrue(can_generate_summary(self.user_id_pro, "Pro", self.mock_db))

    def test_can_generate_summary_free_available(self):
        # Mock usage of 2
        mock_usage = SummaryUsage(user_id=self.user_id_free, date=self.today_str, count=2)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_usage
        self.assertTrue(can_generate_summary(self.user_id_free, "Free", self.mock_db))

    def test_can_generate_summary_free_exhausted(self):
        # Mock usage of 3
        mock_usage = SummaryUsage(user_id=self.user_id_free, date=self.today_str, count=3)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_usage
        self.assertFalse(can_generate_summary(self.user_id_free, "Free", self.mock_db))

    # --- Test record_summary_usage ---

    def test_record_summary_usage_new_record(self):
        # Mock: No existing record
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        record_summary_usage(self.user_id_free, self.mock_db)
        
        # Assert query was run correctly
        self.mock_db.query.assert_called_once()
        # Assert new record was added
        self.mock_db.add.assert_called_once()
        # Assert flush was called
        self.mock_db.flush.assert_called_once()

    def test_record_summary_usage_existing_record(self):
        # Mock: Existing record with count 1
        mock_usage = SummaryUsage(user_id=self.user_id_free, date=self.today_str, count=1)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_usage
        
        record_summary_usage(self.user_id_free, self.mock_db)
        
        # Assert record was updated (count incremented)
        self.assertEqual(mock_usage.count, 2)
        # Assert add was called (since it already exists)
        self.mock_db.add.assert_called_once()
        # Assert flush was called
        self.mock_db.flush.assert_called_once()

if __name__ == '__main__':
    unittest.main()