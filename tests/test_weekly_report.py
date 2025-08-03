import logging
import pytest
from datetime import datetime, timedelta, timezone
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

logger.info("=== Loading test_weekly_report module ===")


def test_weekly_report_integration(db):
    """
    Test weekly report generation with data aggregation and anomaly detection
    using the live emulator. This is a full integration test.
    """
    logger.info("=== Starting test_weekly_report_integration ===")
    
    now = datetime.now(timezone.utc)
    logger.info(f"Test timestamp: {now}")
    
    # --- Setup: Create mock data in Firestore ---
    logger.info("Setting up mock data in Firestore...")
    
    created_docs = []  # Track created documents for cleanup
    
    try:
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
        created_docs.append(("reports", last_week_report_id))
        
        # 2. Recent generation requests (within the last 7 days) for the current report
        logger.info("Creating recent generation requests...")
        
        # Generation request 1: Successful
        gen1_data = {
            "userId": "user1",
            "model": "model-a",
            "style": "anime",
            "color": "vibrant",
            "size": "1024x1024",
            "cost": 3,
            "status": "completed",
            "createdAt": now - timedelta(days=3)
        }
        gen1_ref = db.collection("generationRequests").add(gen1_data)
        created_docs.append(("generationRequests", gen1_ref[1].id))
        logger.info(f"Created generation request 1: {gen1_ref[1].id}")
        
        # Generation request 2: Failed (will test refund tracking)
        gen2_data = {
            "userId": "user2",
            "model": "model-a",
            "style": "anime",
            "color": "vibrant",
            "size": "512x512",
            "cost": 1,
            "status": "failed",
            "createdAt": now - timedelta(days=2)
        }
        gen2_ref = db.collection("generationRequests").add(gen2_data)
        created_docs.append(("generationRequests", gen2_ref[1].id))
        logger.info(f"Created generation request 2: {gen2_ref[1].id}")
        
        # Generation request 3: Another successful
        gen3_data = {
            "userId": "user3",
            "model": "model-b",
            "style": "realistic",
            "color": "monochrome",
            "size": "1024x1792",
            "cost": 4,
            "status": "completed",
            "createdAt": now - timedelta(days=1)
        }
        gen3_ref = db.collection("generationRequests").add(gen3_data)
        created_docs.append(("generationRequests", gen3_ref[1].id))
        logger.info(f"Created generation request 3: {gen3_ref[1].id}")
        
        logger.info("Mock data setup completed")
        
        # --- Call the scheduleWeeklyReport function directly ---
        logger.info("Calling scheduleWeeklyReport function...")
        from functions.main import scheduleWeeklyReport
        
        # Create a mock event
        class MockEvent:
            def __init__(self):
                self.job_name = "test-weekly-report"
                # Remove schedule attribute as it's causing issues
                self.headers = {}
        
                    # Call the actual function
            report_response = scheduleWeeklyReport(MockEvent())
            logger.info(f"Report generation result: {report_response}")
            
            # Function returns a Response object, not the actual report
            # Get the report from Firestore
            report_id = f"report_{now.strftime('%Y-%m-%d')}"
            saved_report = db.collection("reports").document(report_id).get()
            if saved_report.exists:
                report_result = saved_report.to_dict()
                logger.info(f"Retrieved saved report from Firestore: {report_id}")
            else:
                raise Exception("Report was not saved to Firestore")
        
        # --- Verify the report was created correctly ---
        logger.info("Verifying generated report...")
        
        # Check basic metrics
        assert report_result["totalRequests"] == 3
        logger.info("Total requests verification passed")
        
        assert report_result["totalCreditsSpent"] == 7  # 3 + 4 (failed not counted)
        logger.info("Total credits spent verification passed")
        
        assert report_result["totalCreditsRefunded"] == 1  # The failed request
        logger.info("Total credits refunded verification passed")
        
        success_rate = (2 / 3) * 100  # 2 out of 3 succeeded
        assert abs(report_result["successRate"] - success_rate) < 0.1
        logger.info("Success rate verification passed")
        
        # Check aggregations
        logger.info("Checking model aggregations...")
        assert "model-a" in report_result["byModel"]
        assert "model-b" in report_result["byModel"]
        assert report_result["byModel"]["model-a"]["total"] == 2
        assert report_result["byModel"]["model-a"]["completed"] == 1
        assert report_result["byModel"]["model-a"]["failed"] == 1
        logger.info("Model aggregation verification passed")
        
        logger.info("Checking style aggregations...")
        assert "anime" in report_result["byStyle"]
        assert "realistic" in report_result["byStyle"]
        logger.info("Style aggregation verification passed")
        
        logger.info("Checking size aggregations...")
        assert "1024x1024" in report_result["bySize"]
        assert "512x512" in report_result["bySize"]
        assert "1024x1792" in report_result["bySize"]
        logger.info("Size aggregation verification passed")
        
        # Check for anomalies
        logger.info("Checking anomaly detection...")
        anomalies = report_result["anomalies"]
        logger.info(f"Detected anomalies: {anomalies}")
        
        # The test should detect a drop in success rate (80% -> ~66.7%)
        # and possibly other anomalies
        assert len(anomalies) > 0
        logger.info("Anomaly detection verification passed")
        
        # Verify the report was saved to Firestore
        logger.info("Verifying report was saved to Firestore...")
        report_id = f"report_{now.strftime('%Y-%m-%d')}"
        saved_report = db.collection("reports").document(report_id).get()
        assert saved_report.exists
        logger.info("Report persistence verification passed")
        
        logger.info("test_weekly_report_integration completed successfully")
        
    finally:
        # Cleanup
        logger.info("Cleaning up test data...")
        for collection, doc_id in created_docs:
            try:
                db.collection(collection).document(doc_id).delete()
                logger.info(f"Deleted {collection}/{doc_id}")
            except Exception as e:
                logger.warning(f"Cleanup error for {collection}/{doc_id}: {e}")
        
        # Also delete the generated report
        try:
            report_id = f"report_{now.strftime('%Y-%m-%d')}"
            db.collection("reports").document(report_id).delete()
            logger.info(f"Deleted generated report: {report_id}")
        except Exception as e:
            logger.warning(f"Cleanup error for generated report: {e}")
        
        logger.info("Test data cleanup completed")

logger.info("test_weekly_report module loaded successfully")