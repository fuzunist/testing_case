import logging
import pytest
from firebase_admin import firestore
from datetime import datetime, timedelta, timezone
from functions.main import scheduleWeeklyReport, ScheduledEvent
import time

# Configure logging for this test module
logger = logging.getLogger(__name__)

logger.info("=== Loading test_weekly_report module ===")

def test_weekly_report_integration(app_client):
    """
    Test weekly report generation with data aggregation and anomaly detection
    using the live emulator. This is a full integration test.
    """
    logger.info("=== Starting test_weekly_report_integration ===")
    
    db = firestore.client()
    now = datetime.now(timezone.utc)
    logger.info(f"Test timestamp: {now}")

    # --- Setup: Create mock data in Firestore ---
    logger.info("Setting up mock data in Firestore...")
    
    # 1. A previous report for anomaly comparison
    logger.info("Creating previous week's report for anomaly comparison...")
    last_week_report_data = {
        "totalRequests": 10,
        "totalCreditsSpent": 30,
        "successRate": 80.0,
        "byModel": {
            "model-a": {"total": 10, "completed": 8, "failed": 2, "failureRate": 20.0}
        },
        "byStyle": {}, "bySize": {}, "anomalies": [],
        "generatedAt": now - timedelta(days=7)
    }
    last_week_report_id = f"report_{(now - timedelta(days=7)).strftime('%Y-%m-%d')}"
    logger.info(f"Creating previous report with ID: {last_week_report_id}")
    logger.info(f"Previous report data: {last_week_report_data}")
    db.collection("reports").document(last_week_report_id).set(last_week_report_data)
    logger.info("Previous week's report created successfully")

    # 2. Generation requests for the current week
    logger.info("Creating generation requests for current week...")
    requests_ref = db.collection("generationRequests")
    # Simulate a spike in requests (25 vs 10) and a drop in success rate
    logger.info("Creating 25 generation requests with 52% success rate (significant drop from 80%)")
    
    completed_count = 0
    failed_count = 0
    
    for i in range(25):
        is_completed = i % 2 == 0 # 52% success rate, a significant drop from 80%
        if is_completed:
            completed_count += 1
        else:
            failed_count += 1
            
        request_data = {
            "userId": f"user{i}",
            "model": "model-a",
            "style": "cyberpunk",
            "size": "1024x1024", # 3 credits
            "status": "completed" if is_completed else "failed",
            "cost": 3 if is_completed else 3, # Cost is deducted, then refunded on fail
            "createdAt": now - timedelta(days=1)
        }
        requests_ref.add(request_data)
        logger.debug(f"Created request {i+1}: {request_data}")
    
    logger.info(f"Created {completed_count} completed and {failed_count} failed requests")
    logger.info("Waiting for writes to commit...")
    time.sleep(1) # Ensure writes are committed before function call
    logger.info("Test data setup completed")

    # --- Call the function ---
    # In a real test environment, this might be a direct call or an HTTP trigger
    # depending on how the scheduled function is exposed for testing.
    # For this case, we call it directly as it's simpler.
    logger.info("Calling scheduleWeeklyReport function...")
    event = ScheduledEvent(data={}, context={})
    report = scheduleWeeklyReport(event)
    logger.info("Weekly report generation completed")

    # --- Assertions ---
    logger.info("=== Starting assertions ===")
    assert report is not None
    logger.info("Report is not None")
    
    # 1. Verify data aggregation
    logger.info("Verifying data aggregation...")
    logger.info(f"Total requests: {report['totalRequests']} (expected: 25)")
    assert report["totalRequests"] == 25
    logger.info("Total requests verification passed")
    
    logger.info(f"Total credits spent: {report['totalCreditsSpent']} (expected: 39)")
    assert report["totalCreditsSpent"] == 39 # 13 completed * 3 credits
    logger.info("Total credits spent verification passed")
    
    logger.info(f"Total credits refunded: {report['totalCreditsRefunded']} (expected: 36)")
    assert report["totalCreditsRefunded"] == 36 # 12 failed * 3 credits
    logger.info("Total credits refunded verification passed")
    
    logger.info(f"Success rate: {report['successRate']}% (expected: ~52%)")
    assert 51 < report["successRate"] < 53 # 13/25 = 52%
    logger.info("Success rate verification passed")
    
    # 2. Verify aggregation by category
    logger.info("Verifying aggregation by category...")
    model_data = report["byModel"]["model-a"]
    logger.info(f"model-a data: {model_data}")
    
    logger.info(f"model-a total: {model_data['total']} (expected: 25)")
    assert model_data["total"] == 25
    logger.info("model-a total verification passed")
    
    logger.info(f"model-a completed: {model_data['completed']} (expected: 13)")
    assert model_data["completed"] == 13
    logger.info("model-a completed verification passed")
    
    logger.info(f"model-a failed: {model_data['failed']} (expected: 12)")
    assert model_data["failed"] == 12
    logger.info("model-a failed verification passed")
    
    logger.info(f"model-a failure rate: {model_data['failureRate']}% (expected: ~48%)")
    assert 47 < model_data["failureRate"] < 49 # 12/25 = 48%
    logger.info("model-a failure rate verification passed")
    
    # 3. Verify anomaly detection
    logger.info("Verifying anomaly detection...")
    anomalies = report.get("anomalies", [])
    logger.info(f"Detected anomalies: {anomalies}")
    assert len(anomalies) > 1
    logger.info("Anomaly count verification passed")
    
    anomalies_text = " ".join(anomalies)
    logger.info(f"Anomalies text: {anomalies_text}")
    
    logger.info("Checking for 'Unusual spike in total requests' anomaly...")
    assert "Unusual spike in total requests" in anomalies_text
    logger.info("Total requests spike anomaly verification passed")
    
    logger.info("Checking for 'Drastic drop in success rate' anomaly...")
    assert "Drastic drop in success rate" in anomalies_text
    logger.info("Success rate drop anomaly verification passed")
    
    # 4. Verify the new report was saved to Firestore
    logger.info("Verifying report was saved to Firestore...")
    new_report_id = f"report_{now.strftime('%Y-%m-%d')}"
    logger.info(f"Checking for saved report with ID: {new_report_id}")
    
    report_snapshot = db.collection("reports").document(new_report_id).get()
    assert report_snapshot.exists
    logger.info("Report exists in Firestore")
    
    saved_data = report_snapshot.to_dict()
    logger.info(f"Saved report data: {saved_data}")
    
    logger.info(f"Saved total requests: {saved_data['totalRequests']} (expected: 25)")
    assert saved_data["totalRequests"] == 25
    logger.info("Saved total requests verification passed")
    
    logger.info(f"Saved success rate: {saved_data['successRate']}% (expected: {report['successRate']}%)")
    assert saved_data["successRate"] == report["successRate"]
    logger.info("Saved success rate verification passed")
    
    logger.info("=== test_weekly_report_integration completed successfully ===")

logger.info("test_weekly_report module loaded successfully")