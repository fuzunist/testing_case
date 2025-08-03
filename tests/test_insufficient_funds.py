import logging
import pytest
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_insufficient_funds module ===")


@pytest.fixture
def expensive_payload():
    """
    Provides a payload for an expensive generation request (4 credits).
    """
    logger.info("=== Setting up expensive_payload fixture ===")
    payload = {
        "userId": "testUserInsufficient",
        "model": "model-b",
        "style": "cyberpunk",
        "color": "neon",
        "size": "1024x1792",  # Costs 4 credits (the most expensive)
        "prompt": "A cyberpunk city in neon colors."
    }
    logger.info(f"Created expensive payload: {payload}")
    return payload


def test_insufficient_credits_rejection(app_client, db, expensive_payload):
    """
    Test that a request from a user with insufficient credits is rejected
    and no database changes are made. This is an integration test.
    """
    logger.info("=== Starting test_insufficient_credits_rejection ===")
    logger.info(f"Test parameters: {expensive_payload}")
    
    # --- Setup: Create a user with insufficient credits in Firestore ---
    logger.info("Setting up test user with insufficient credits...")
    user_ref = db.collection("users").document(expensive_payload["userId"])
    
    try:
        # User has only 2 credits but needs 4
        initial_credits = 2
        logger.info(f"Creating user '{expensive_payload['userId']}' with {initial_credits} credits (needs 4)")
        user_ref.set({"credits": initial_credits})
        
        # --- Make the request ---
        logger.info(f"Making POST request to {BASE_URL}")
        response = app_client.post(BASE_URL, json=expensive_payload)
        logger.info(f"Response status code: {response.status_code}")
        
        # --- Assertions ---
        # 1. Check API response
        logger.info("Checking API response...")
        assert response.status_code == 400  # Bad Request
        logger.info("Response status code is 400 (Bad Request)")
        
        response_text = response.get_data(as_text=True)
        logger.info(f"Response text: {response_text}")
        assert "Insufficient credits" in response_text
        logger.info("Error message verification passed")
        
        # 2. Verify no database changes occurred
        logger.info("Verifying database state remained unchanged...")
        
        # Check user credits were NOT deducted
        logger.info("Checking user credits...")
        user_snapshot = user_ref.get()
        assert user_snapshot.exists
        final_credits = user_snapshot.to_dict()["credits"]
        logger.info(f"Final credits: {final_credits}")
        assert final_credits == initial_credits  # No change
        logger.info("User credits unchanged verification passed")
        
        # Check no generation request was created
        logger.info("Checking generation requests...")
        gen_requests = list(db.collection("generationRequests")
                          .where("userId", "==", expensive_payload["userId"])
                          .stream())
        logger.info(f"Found {len(gen_requests)} generation requests for user")
        assert len(gen_requests) == 0
        logger.info("No generation request created verification passed")
        
        # Check no transaction was logged
        logger.info("Checking transaction logs...")
        transactions = list(user_ref.collection("transactions").stream())
        logger.info(f"Found {len(transactions)} transactions for user")
        assert len(transactions) == 0
        logger.info("No transaction logged verification passed")
        
        logger.info("test_insufficient_credits_rejection completed successfully")
        
    finally:
        # Cleanup
        logger.info(f"Cleaning up test data for user '{expensive_payload['userId']}'")
        try:
            user_ref.delete()
            logger.info("Test data cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")