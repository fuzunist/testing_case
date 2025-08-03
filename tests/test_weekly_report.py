import json
import logging
from datetime import datetime, timedelta, timezone
import pytest
from functions.main import scheduleWeeklyReport

logger = logging.getLogger(__name__)

class MockEvent:
    """A mock event object for testing scheduled functions, defined at module level."""
    def __init__(self):
        self.job_name = "test-weekly-report-manual-trigger"
        self.headers = {}

def test_weekly_report_integration(db):
    """
    Tests the full lifecycle of the weekly report generation:
    1. Sets up mock data (a previous report and recent generation requests).
    2. Triggers the 'scheduleWeeklyReport' function.
    3. Verifies the generated report's metrics (totals, rates).
    4. Checks that anomaly detection runs.
    5. Confirms the report is saved correctly to Firestore.
    6. Cleans up all created test data.
    """
    logger.info("=== Starting test_weekly_report_integration ===")
    now = datetime.now(timezone.utc)
    created_docs = []  # To track all documents created during the test for cleanup

    try:
        # --- Setup: Create mock data in Firestore ---
        # 1. A previous week's report for anomaly comparison
        last_week_report_data = {
            "totalRequests": 10,
            "totalCreditsSpent": 30,
            "successRate": 80.0,
            "byModel": {"model-a": {"total": 10, "completed": 8, "failed": 2, "failureRate": 20.0}},
            "byStyle": {}, "bySize": {}, "anomalies": [],
            "generatedAt": now - timedelta(days=7)
        }
        last_week_report_id = f"report_{(now - timedelta(days=7)).strftime('%Y-%m-%d')}"
        db.collection("reports").document(last_week_report_id).set(last_week_report_data)
        created_docs.append(("reports", last_week_report_id))
        logger.info(f"Created previous report for comparison: {last_week_report_id}")

        # 2. Recent generation requests to be included in the new report
        requests_data = [
            {"userId": "user1", "model": "model-a", "style": "anime", "cost": 3, "status": "completed", "createdAt": now - timedelta(days=3)},
            {"userId": "user2", "model": "model-a", "style": "anime", "cost": 1, "status": "failed", "createdAt": now - timedelta(days=2)},
            {"userId": "user3", "model": "model-b", "style": "realistic", "cost": 4, "status": "completed", "createdAt": now - timedelta(days=1)}
        ]
        for req_data in requests_data:
            _, gen_ref = db.collection("generationRequests").add(req_data)
            created_docs.append(("generationRequests", gen_ref.id))
        logger.info(f"Created {len(requests_data)} recent generation requests.")

        # --- Trigger the weekly report function ---
        logger.info("Calling scheduleWeeklyReport function...")
        # The function, when triggered via HTTP, returns a Response object.
        # The test needs to handle this, but for direct invocation, we expect a dict.
        # Let's adjust the test to call the underlying function logic if possible,
        # or handle the Response object correctly.
        
        # In this setup, scheduleWeeklyReport is imported directly and returns a dict.
        # The issue might be how the test environment is set up. Let's assume direct call.
        scheduleWeeklyReport(MockEvent())
    
        # --- Assertions ---
        # Instead of checking the return value (which is not standard for scheduled functions),
        # we will verify the outcome directly from Firestore.
        report_id = f"report_{now.strftime('%Y-%m-%d')}"
        report_ref = db.collection("reports").document(report_id)
        created_docs.append(("reports", report_id)) # Add to cleanup
        
        report_doc = report_ref.get()
        assert report_doc.exists, f"Report document '{report_id}' was not created in Firestore."

        report_data = report_doc.to_dict()
        logger.info(f"Successfully fetched created report from Firestore: {report_data}")

        # 1. Verify key metrics in the generated report data
        assert report_data["totalRequests"] == 3
        assert report_data["totalCreditsSpent"] == 7
        assert report_data.get("totalCreditsRefunded") == 1 # 1 (user2)
        assert pytest.approx(report_data.get("successRate", 0), 0.01) == (2/3) * 100

        # 2. Verify anomaly detection ran
        assert "anomalies" in report_data
        assert isinstance(report_data["anomalies"], list)

        # 3. Verify the report was saved correctly in Firestore
        # The report_id was already added to created_docs for cleanup
        logger.info(f"Verified report was saved to Firestore: {report_id}")

        logger.info("All assertions for weekly report test passed successfully.")

    finally:
        # --- Cleanup: Delete all documents created during this test ---
        logger.info(f"Cleaning up {len(created_docs)} created test documents...")
        # Use set to avoid duplicate cleanup attempts (e.g., if report_id was predictable)
        for collection, doc_id in set(created_docs):
            try:
                db.collection(collection).document(doc_id).delete()
                logger.info(f"Deleted {collection}/{doc_id}")
            except Exception as e:
                logger.error(f"Error during cleanup of {collection}/{doc_id}: {e}")
        logger.info("Test data cleanup completed.")