import logging
from unittest.mock import patch
import pytest
from firebase_admin import firestore
from datetime import datetime, timezone

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/getUserCredits"

logger.info("=== Loading test_get_user_credits module ===")

def test_get_user_credits_success(app_client):
    """
    Test successful retrieval of a user's credits and transaction history
    using the live emulator. This is an integration test.
    """
    logger.info("=== Starting test_get_user_credits_success ===")
    
    # --- Setup: Create a user with a transaction history in Firestore ---
    logger.info("Setting up test data in Firestore...")
    db = firestore.client()
    user_id = "userWithHistory"
    user_ref = db.collection("users").document(user_id)
    
    # Set initial credits
    logger.info(f"Creating user '{user_id}' with 97 credits")
    user_ref.set({"credits": 97})
    
    # Create transaction records
    logger.info("Creating transaction history...")
    trans_ref = user_ref.collection("transactions")
    
    logger.info("Creating transaction t1 (deduction of 5 credits)")
    trans_ref.document("t1").set({
        "type": "deduction",
        "credits": 5,
        "generationRequestId": "gen1",
        "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    })
    
    logger.info("Creating transaction t2 (refund of 2 credits)")
    trans_ref.document("t2").set({
        "type": "refund",
        "credits": 2,
        "generationRequestId": "gen2",
        "timestamp": datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    })
    
    logger.info("Creating transaction t3 (deduction of 0 credits - freebie)")
    trans_ref.document("t3").set({ # Another deduction
        "type": "deduction",
        "credits": 0, # freebie
        "generationRequestId": "gen3",
        "timestamp": datetime(2023, 1, 3, 12, 0, 0, tzinfo=timezone.utc)
    })
    
    logger.info("Test data setup completed")

    # --- Make the request ---
    logger.info(f"Making GET request to {BASE_URL}?userId={user_id}")
    response = app_client.get(f"{BASE_URL}?userId={user_id}")
    logger.info(f"Response status code: {response.status_code}")

    # --- Assertions ---
    logger.info("Checking response status...")
    assert response.status_code == 200
    logger.info("Response status is 200 (OK)")
    
    data = response.get_json()
    logger.info(f"Response data: {data}")
    
    # Verify current credits
    logger.info("Verifying current credits...")
    assert data["currentCredits"] == 97
    logger.info("Current credits verification passed")
    
    # Verify transaction history
    logger.info("Verifying transaction history...")
    transactions = data["transactions"]
    logger.info(f"Found {len(transactions)} transactions")
    assert len(transactions) == 3
    logger.info("Transaction count verification passed")
    
    # Transactions should be sorted by timestamp descending
    logger.info("Verifying transaction order (should be sorted by timestamp descending)...")
    
    logger.info(f"First transaction (most recent): {transactions[0]}")
    assert transactions[0]["id"] == "t3"
    assert transactions[0]["type"] == "deduction"
    logger.info("First transaction verification passed")
    
    logger.info(f"Second transaction: {transactions[1]}")
    assert transactions[1]["id"] == "t2"
    assert transactions[1]["type"] == "refund"
    assert transactions[1]["credits"] == 2
    logger.info("Second transaction verification passed")
    
    logger.info(f"Third transaction (oldest): {transactions[2]}")
    assert transactions[2]["id"] == "t1"
    assert transactions[2]["type"] == "deduction"
    logger.info("Third transaction verification passed")
    
    logger.info("Verifying timestamp field exists...")
    assert "timestamp" in transactions[0]
    logger.info("Timestamp field verification passed")
    
    logger.info("=== test_get_user_credits_success completed successfully ===")


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
    logger.info("Response status is 404 (Not Found)")
    
    response_text = response.get_data(as_text=True)
    logger.info(f"Response text: {response_text}")
    assert "User not found" in response_text
    logger.info("Error message verification passed")
    
    logger.info("=== test_get_user_credits_not_found completed successfully ===")

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
    logger.info("Response status is 400 (Bad Request)")
    
    response_text = response.get_data(as_text=True)
    logger.info(f"Response text: {response_text}")
    assert "userId parameter is required" in response_text
    logger.info("Error message verification passed")
    
    logger.info("=== test_get_user_credits_missing_userid completed successfully ===")

logger.info("test_get_user_credits module loaded successfully")