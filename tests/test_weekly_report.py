import pytest
from firebase_admin import firestore
from datetime import datetime, timedelta, timezone
from functions.main import scheduleWeeklyReport, ScheduledEvent
import time

def test_weekly_report_integration(app_client):
    """
    Test weekly report generation with data aggregation and anomaly detection
    using the live emulator. This is a full integration test.
    """
    db = firestore.client()
    now = datetime.now(timezone.utc)

    # --- Setup: Create mock data in Firestore ---
    
    # 1. A previous report for anomaly comparison
    last_week_report_data = {
        "totalRequests": 10,
        "totalCreditsSpent": 30,
        "successRate": 80.0,
        "byModel": {
            "Model A": {"total": 10, "completed": 8, "failed": 2, "failureRate": 20.0}
        },
        "byStyle": {}, "bySize": {}, "anomalies": [],
        "generatedAt": now - timedelta(days=7)
    }
    db.collection("reports").document(f"report_{(now - timedelta(days=7)).strftime('%Y-%m-%d')}").set(last_week_report_data)

    # 2. Generation requests for the current week
    requests_ref = db.collection("generationRequests")
    # Simulate a spike in requests (25 vs 10) and a drop in success rate
    for i in range(25):
        is_completed = i % 2 == 0 # 52% success rate, a significant drop from 80%
        requests_ref.add({
            "userId": f"user{i}",
            "model": "Model A",
            "style": "cyberpunk",
            "size": "1024x1024", # 3 credits
            "status": "completed" if is_completed else "failed",
            "cost": 3 if is_completed else 3, # Cost is deducted, then refunded on fail
            "createdAt": now - timedelta(days=1)
        })
    time.sleep(1) # Ensure writes are committed before function call

    # --- Call the function ---
    # In a real test environment, this might be a direct call or an HTTP trigger
    # depending on how the scheduled function is exposed for testing.
    # For this case, we call it directly as it's simpler.
    event = ScheduledEvent(data={}, context={})
    report = scheduleWeeklyReport(event)

    # --- Assertions ---
    assert report is not None
    
    # 1. Verify data aggregation
    assert report["totalRequests"] == 25
    assert report["totalCreditsSpent"] == 39 # 13 completed * 3 credits
    assert report["totalCreditsRefunded"] == 36 # 12 failed * 3 credits
    assert 51 < report["successRate"] < 53 # 13/25 = 52%
    
    # 2. Verify aggregation by category
    assert report["byModel"]["Model A"]["total"] == 25
    assert report["byModel"]["Model A"]["completed"] == 13
    assert report["byModel"]["Model A"]["failed"] == 12
    assert 47 < report["byModel"]["Model A"]["failureRate"] < 49 # 12/25 = 48%
    
    # 3. Verify anomaly detection
    anomalies = report.get("anomalies", [])
    assert len(anomalies) > 1
    anomalies_text = " ".join(anomalies)
    assert "Unusual spike in total requests" in anomalies_text
    assert "Drastic drop in success rate" in anomalies_text
    
    # 4. Verify the new report was saved to Firestore
    new_report_id = f"report_{now.strftime('%Y-%m-%d')}"
    report_snapshot = db.collection("reports").document(new_report_id).get()
    assert report_snapshot.exists
    saved_data = report_snapshot.to_dict()
    assert saved_data["totalRequests"] == 25
    assert saved_data["successRate"] == report["successRate"]