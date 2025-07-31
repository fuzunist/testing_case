import logging
from unittest.mock import patch
import pytest
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_insufficient_funds module ===")

@pytest.fixture
def expensive_payload():
    """Provides a payload that costs more credits than the user has."""
    logger.info("=== Setting up expensive_payload fixture ===")
    payload = {
        "userId": "testUserInsufficient",
        "model": "Model B",
        "style": "cyberpunk",
        "color": "neon",
        "size": "1024x1792", # Costs 4 credits
        "prompt": "A cyberpunk city in neon colors."
    }
    logger.info(f"Created expensive payload: {payload}")
    return payload

def test_insufficient_credits_rejection(app_client, expensive_payload):
    """
    Test that a request from a user with insufficient credits is rejected
    and no database changes are made. This is an integration test.
    """
    logger.info("=== Starting test_insufficient_credits_rejection ===")
    logger.info(f"Test parameters: {expensive_payload}")
    
    # --- Setup: Create a user with insufficient credits in Firestore ---
    logger.info("Setting up test user with insufficient credits...")
    db = firestore.client()
    user_ref = db.collection("users").document(expensive_payload["userId"])
    initial_credits = 2 # Cost is 4, user only has 2
    logger.info(f"Creating user '{expensive_payload['userId']}' with {initial_credits} credits (cost will be 4)")
    user_ref.set({"credits": initial_credits})
    logger.info("Test user setup completed")

    # --- Make the request ---
    logger.info(f"Making POST request to {BASE_URL}")
    response = app_client.post(BASE_URL, json=expensive_payload)
    logger.info(f"Response status code: {response.status_code}")
    
    # --- Assertions ---
    # 1. Check API response for the correct error
    logger.info("Checking API response...")
    assert response.status_code == 412 # FAILED_PRECONDITION
    logger.info("Response status is 412 (Failed Precondition)")
    
    response_text = response.get_data(as_text=True)
    logger.info(f"Response text: {response_text}")
    assert "Insufficient credits" in response_text
    logger.info("Error message verification passed")

    # 2. Verify that no data was changed in Firestore
    logger.info("Verifying that no database changes were made...")
    
    # User credits should remain unchanged
    logger.info("Checking user credits remain unchanged...")
    user_snapshot = user_ref.get()
    final_credits = user_snapshot.to_dict()["credits"]
    logger.info(f"Final credits: {final_credits} (should be {initial_credits})")
    assert final_credits == initial_credits
    logger.info("User credits verification passed - no deduction occurred")

    # No generation request should have been created
    logger.info("Checking that no generation request was created...")
    requests_query = db.collection("generationRequests").where("userId", "==", expensive_payload["userId"]).stream()
    request_count = len(list(requests_query))
    logger.info(f"Found {request_count} generation requests (should be 0)")
    assert request_count == 0
    logger.info("Generation request verification passed - no request was created")

    # No transactions should have been logged
    logger.info("Checking that no transactions were logged...")
    transactions_query = user_ref.collection("transactions").stream()
    transaction_count = len(list(transactions_query))
    logger.info(f"Found {transaction_count} transactions (should be 0)")
    assert transaction_count == 0
    logger.info("Transaction verification passed - no transactions were logged")
    
    logger.info("=== test_insufficient_credits_rejection completed successfully ===")

logger.info("test_insufficient_funds module loaded successfully")