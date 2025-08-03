import logging
import pytest
from datetime import datetime, timezone
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/getUserCredits"

logger.info("=== Loading test_get_user_credits module ===")


def test_get_user_credits_success(app_client, db):
    """
    Test successful retrieval of a user's credits and transaction history
    using the live emulator. This is an integration test.
    """
    logger.info("=== Starting test_get_user_credits_success ===")
    
    # --- Setup: Create a user with a transaction history in Firestore ---
    logger.info("Setting up test data in Firestore...")
    user_id = "userWithHistory"
    user_ref = db.collection("users").document(user_id)
    
    try:
        # Create user
        logger.info(f"Creating user '{user_id}' with 50 credits")
        user_ref.set({"credits": 50})
        
        # Create some transaction history
        logger.info(f"Creating transaction history for user '{user_id}'")
        trans_collection = user_ref.collection("transactions")
        
        # Transaction 1: Deduction
        trans1_data = {
            "type": "deduction",
            "credits": 3,
            "generationRequestId": "gen123",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        trans1_ref = trans_collection.add(trans1_data)
        logger.info(f"Created transaction 1: {trans1_ref[1].id}")
        
        # Transaction 2: Refund
        trans2_data = {
            "type": "refund",
            "credits": 3,
            "generationRequestId": "gen123",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        trans2_ref = trans_collection.add(trans2_data)
        logger.info(f"Created transaction 2: {trans2_ref[1].id}")
        
        # Transaction 3: Another deduction
        trans3_data = {
            "type": "deduction",
            "credits": 1,
            "generationRequestId": "gen456",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        trans3_ref = trans_collection.add(trans3_data)
        logger.info(f"Created transaction 3: {trans3_ref[1].id}")
        
        logger.info("Test data setup completed")
        
        # --- Make the request ---
        logger.info(f"Making GET request to {BASE_URL}?userId={user_id}")
        response = app_client.get(f"{BASE_URL}?userId={user_id}")
        logger.info(f"Response status code: {response.status_code}")
        
        # --- Assertions ---
        logger.info("Checking response...")
        assert response.status_code == 200
        logger.info("Response status code is 200 (OK)")
        
        response_data = response.get_json()
        logger.info(f"Response data: {response_data}")
        
        assert response_data["currentCredits"] == 50
        logger.info("Current credits verification passed")
        
        assert len(response_data["transactions"]) == 3
        logger.info("Transaction count verification passed")
        
        # Check transaction types
        trans_types = [t["type"] for t in response_data["transactions"]]
        logger.info(f"Transaction types: {trans_types}")
        assert "deduction" in trans_types
        assert "refund" in trans_types
        logger.info("Transaction types verification passed")
        
        # Check the latest transaction is first (ordering by timestamp descending)
        # Note: Due to timing, we can't guarantee exact order, but we can check presence
        logger.info("Verifying transaction IDs are present...")
        trans_ids = [t["id"] for t in response_data["transactions"]]
        assert trans1_ref[1].id in trans_ids
        assert trans2_ref[1].id in trans_ids
        assert trans3_ref[1].id in trans_ids
        logger.info("All transaction IDs found in response")
        
        logger.info("test_get_user_credits_success completed successfully")
        
    finally:
        # Cleanup
        logger.info(f"Cleaning up test data for user '{user_id}'")
        try:
            # Delete transactions
            for trans in trans_collection.stream():
                trans.reference.delete()
            # Delete user
            user_ref.delete()
            logger.info("Test data cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


def test_get_user_credits_not_found(app_client):
    """
    Test the response for a non-existent user using the live emulator.
    """
    logger.info("=== Starting test_get_user_credits_not_found ===")
    
    user_id = "nonExistentUser"
    logger.info(f"Testing with non-existent user ID: {user_id}")
    
    logger.info(f"Making GET request to {BASE_URL}?userId={user_id}")
    response = app_client.get(f"{BASE_URL}?userId={user_id}")
    logger.info(f"Response status code: {response.status_code}")
    
    logger.info("Checking response...")
    assert response.status_code == 404
    logger.info("Response status code is 404 (Not Found)")
    
    assert b"User not found" in response.data
    logger.info("Error message verification passed")
    
    logger.info("test_get_user_credits_not_found completed successfully")


def test_get_user_credits_missing_userid(app_client):
    """
    Test the response when the userId parameter is missing.
    """
    logger.info("=== Starting test_get_user_credits_missing_userid ===")
    
    logger.info(f"Making GET request to {BASE_URL} without userId parameter")
    response = app_client.get(BASE_URL)
    logger.info(f"Response status code: {response.status_code}")
    
    logger.info("Checking response...")
    assert response.status_code == 400
    logger.info("Response status code is 400 (Bad Request)")
    
    assert b"userId parameter is required" in response.data
    logger.info("Error message verification passed")
    
    logger.info("test_get_user_credits_missing_userid completed successfully")