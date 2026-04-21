import unittest
import asyncio
from unittest.mock import patch, MagicMock
from app.webhook_worker import deliver_webhooks_for_alert, run_webhook_delivery
from app.models import Alert, db, Database

class TestWebhookWorker(unittest.TestCase):
    
    def setUp(self):
        # Reset the global mock database before each test
        global db
        db = Database()
        
        # Reset the mock HTTP client state
        if hasattr(deliver_webhooks_for_alert, 'mock_http_post'):
            deliver_webhooks_for_alert.mock_http_post.attempt_count = 0

    @patch('app.webhook_worker.db')
    @patch('app.webhook_worker.mock_http_post')
    async def test_successful_delivery(self, mock_http_post, mock_db):
        """Tests successful delivery on the first attempt."""
        # Setup Alert
        alert = Alert(
            id=101, 
            rule_id=1, 
            message="Success Test", 
            severity="INFO", 
            timestamp="2026-04-21T10:00:00Z", 
            webhook_delivered=False, 
            webhook_url="https://hooks.slack.com/success"
        )
        mock_db.alerts = {101: alert}
        
        # Setup Mock HTTP response
        mock_http_post.return_value = True
        
        # Run
        await deliver_webhooks_for_alert(101)
        
        # Assertions
        mock_http_post.assert_called_once()
        self.assertTrue(alert.webhook_delivered)
        mock_db.update_alert.assert_called_once_with(alert)

    @patch('app.webhook_worker.db')
    @patch('app.webhook_worker.mock_http_post')
    async def test_delivery_with_retries(self, mock_http_post, mock_db):
        """Tests delivery requiring multiple retries (e.g., 3 attempts)."""
        # Setup Alert
        alert = Alert(
            id=102, 
            rule_id=2, 
            message="Retry Test", 
            severity="WARNING", 
            timestamp="2026-04-21T10:01:00Z", 
            webhook_delivered=False, 
            webhook_url="https://hooks.slack.com/fail_once"
        )
        mock_db.alerts = {102: alert}
        
        # Setup Mock HTTP response: Fail twice, succeed on third
        mock_http_post.side_effect = [False, False, True]
        
        # Run
        await deliver_webhooks_for_alert(102)
        
        # Assertions
        self.assertEqual(mock_http_post.call_count, 3)
        self.assertTrue(alert.webhook_delivered)
        mock_db.update_alert.assert_called_once_with(alert)

    @patch('app.webhook_worker.db')
    @patch('app.webhook_worker.mock_http_post')
    async def test_delivery_failure_after_max_retries(self, mock_http_post, mock_db):
        """Tests delivery failing after all 3 attempts."""
        # Setup Alert
        alert = Alert(
            id=103, 
            rule_id=3, 
            message="Max Retry Test", 
            severity="CRITICAL", 
            timestamp="2026-04-21T10:02:00Z", 
            webhook_delivered=False, 
            webhook_url="https://hooks.slack.com/fail_always"
        )
        mock_db.alerts = {103: alert}
        
        # Setup Mock HTTP response: Fail all three times
        mock_http_post.return_value = False
        
        # Run
        await deliver_webhooks_for_alert(103)
        
        # Assertions
        self.assertEqual(mock_http_post.call_count, 3)
        self.assertFalse(alert.webhook_delivered) # Should remain False
        mock_db.update_alert.assert_called_once_with(alert)

    @patch('app.webhook_worker.db')
    @patch('app.webhook_worker.mock_http_post')
    async def test_run_webhook_delivery_batch(self, mock_http_post, mock_db):
        """Tests the batch runner finds and processes multiple alerts."""
        # Setup Alerts
        alert1 = Alert(id=201, rule_id=1, message="A", severity="INFO", timestamp="T1", webhook_delivered=False, webhook_url="URL1")
        alert2 = Alert(id=202, rule_id=2, message="B", severity="WARN", timestamp="T2", webhook_delivered=False, webhook_url="URL2")
        alert3 = Alert(id=203, rule_id=3, message="C", severity="CRIT", timestamp="T3", webhook_delivered=True, webhook_url="URL3") # Already delivered
        
        mock_db.alerts = {201: alert1, 202: alert2, 203: alert3}
        
        # Setup Mock HTTP response (Success for both 201 and 202)
        mock_http_post.side_effect = [True, True]
        
        # Run
        run_webhook_delivery(limit=5)
        
        # Assertions
        self.assertEqual(mock_http_post.call_count, 2) # Only 2 undelivered alerts
        self.assertTrue(alert1.webhook_delivered)
        self.assertTrue(alert2.webhook_delivered)
        
        # Check that update was called for the delivered ones
        calls = [
            unittest.mock.call(alert1),
            unittest.mock.call(alert2)
        ]
        mock_db.update_alert.assert_has_calls(calls, any_order=True)

if __name__ == '__main__':
    unittest.main()