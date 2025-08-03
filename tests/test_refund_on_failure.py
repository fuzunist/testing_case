import logging
from unittest.mock import patch
import pytest
import time
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_refund_on_failure module ===")


@pytest.fixture
def valid_payload():
    """
    Provides a valid payload for a generation request.
    """
    logger.info("=== Setting up valid_payload fixture ===")
    payload = {
        "userId": "testUserRefund",
        "model": "model-b",
        "style": "sketch",
        "color": "monochrome",
        "size": "512x512",  # Costs 1 credit
        "prompt": "A test prompt for refund logic."
    }
    logger.info(f"Created valid payload: {payload}")
    return payload


def test_refund_on_ai_failure(app_client, db, valid_payload):
    """
    Test that credits are refunded and status is 'failed' when AI generation fails.
    This test modifies the AI failure rate temporarily to ensure failure.
    """
    logger.info("=== Starting test_refund_on_ai_failure ===")
    logger.info(f"Test parameters: {valid_payload}")
    
    # --- Setup: Create the test user in Firestore ---
    logger.info("Setting up test user...")
    user_ref = db.collection("users").document(valid_payload["userId"])
    
    try:
        initial_credits = 10
        logger.info(f"Creating user '{valid_payload['userId']}' with {initial_credits} credits")
        user_ref.set({"credits": initial_credits})
        
        # --- Temporarily modify the AI failure rate to 100% ---
        logger.info("Setting AI failure rate to 100% temporarily")
        from functions.config import AIModelsConfig
        original_failure_rate = AIModelsConfig.DEFAULT_FAILURE_RATE
        AIModelsConfig.DEFAULT_FAILURE_RATE = 1.0  # 100% failure rate
        
        try:
            # --- Make the request ---
            logger.info(f"Making POST request to {BASE_URL}")
            response = app_client.post(BASE_URL, json=valid_payload)
            logger.info(f"Response status code: {response.status_code}")
            
            # --- Assertions ---
            # 1. Check API response for failure
            logger.info("Checking API response...")
            assert response.status_code == 500  # Internal Server Error for AI failure
            logger.info("Response status code is 500 (Internal Server Error)")
            
            response_text = response.get_data(as_text=True)
            logger.info(f"Response text: {response_text}")
            assert "AI generation failed" in response_text
            assert "credits refunded" in response_text
            logger.info("Error message verification passed")
            
            # 2. Wait a moment for the refund to process
            logger.info("Waiting for refund processing...")
            time.sleep(2)
            
            # 3. Verify refund in Firestore
            logger.info("Verifying refund in database...")
            
            # Check that user credits were refunded (should be back to initial)
            logger.info("Checking user credits after refund...")
            user_snapshot = user_ref.get()
            assert user_snapshot.exists
            final_credits = user_snapshot.to_dict()["credits"]
            logger.info(f"Final credits: {final_credits} (should be {initial_credits})")
            assert final_credits == initial_credits  # Credits should be refunded
            logger.info("Credit refund verification passed")
            
            # Check that generation request exists and is marked as 'failed'
            logger.info("Checking generation request status...")
            gen_requests = list(db.collection("generationRequests")
                              .where("userId", "==", valid_payload["userId"])
                              .stream())
            logger.info(f"Found {len(gen_requests)} generation requests")
            assert len(gen_requests) == 1
            
            gen_req_data = gen_requests[0].to_dict()
            logger.info(f"Generation request data: {gen_req_data}")
            assert gen_req_data["status"] == "failed"
            logger.info("Generation request status verification passed")
            
            # Check that transaction history shows both deduction and refund
            logger.info("Checking transaction history...")
            transactions = list(user_ref.collection("transactions")
                              .order_by("timestamp", direction=firestore.Query.ASCENDING)
                              .stream())
            logger.info(f"Found {len(transactions)} transactions")
            assert len(transactions) == 2
            
            # First transaction should be deduction
            trans1_data = transactions[0].to_dict()
            logger.info(f"Transaction 1: {trans1_data}")
            assert trans1_data["type"] == "deduction"
            assert trans1_data["credits"] == 1  # Size 512x512 costs 1 credit
            logger.info("Deduction transaction verification passed")
            
            # Second transaction should be refund
            trans2_data = transactions[1].to_dict()
            logger.info(f"Transaction 2: {trans2_data}")
            assert trans2_data["type"] == "refund"
            assert trans2_data["credits"] == 1
            logger.info("Refund transaction verification passed")
            
            logger.info("test_refund_on_ai_failure completed successfully")
            
        finally:
            # Restore original failure rate
            logger.info(f"Restoring original AI failure rate: {original_failure_rate}")
            AIModelsConfig.DEFAULT_FAILURE_RATE = original_failure_rate
        
    finally:
        # Cleanup
        logger.info(f"Cleaning up test data for user '{valid_payload['userId']}'")
        try:
            # Delete generation requests
            for req in db.collection("generationRequests").where("userId", "==", valid_payload["userId"]).stream():
                req.reference.delete()
            # Delete transactions
            for trans in user_ref.collection("transactions").stream():
                trans.reference.delete()
            # Delete user
            user_ref.delete()
            logger.info("Test data cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")