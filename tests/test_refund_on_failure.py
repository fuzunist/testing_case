import logging
from unittest.mock import patch
import pytest
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_refund_on_failure module ===")

@pytest.fixture
def valid_payload():
    """Provides a valid payload for a generation request."""
    logger.info("=== Setting up valid_payload fixture ===")
    payload = {
        "userId": "testUserRefund",
        "model": "model-b",
        "style": "sketch",
        "color": "monochrome",
        "size": "512x512", # Costs 1 credit
        "prompt": "A test prompt for refund logic."
    }
    logger.info(f"Created valid payload: {payload}")
    return payload

@patch("functions.ai_simulator.AIChat.create")
def test_refund_on_ai_failure(mock_ai_create, app_client, valid_payload):
    """
    Test that credits are refunded and status is 'failed' when AI generation fails.
    This is an integration test using the live emulator.
    """
    logger.info("=== Starting test_refund_on_ai_failure ===")
    logger.info(f"Test parameters: {valid_payload}")
    
    # --- Mock AI behavior to simulate a failure ---
    mock_failure_response = {
        "success": False,
        "error": "Simulated AI failure."
    }
    mock_ai_create.return_value = mock_failure_response
    logger.info(f"Mocked AI failure response: {mock_failure_response}")

    # --- Setup: Create the test user in Firestore ---
    logger.info("Setting up test user...")
    db = firestore.client()
    user_ref = db.collection("users").document(valid_payload["userId"])
    initial_credits = 50
    logger.info(f"Creating user '{valid_payload['userId']}' with {initial_credits} credits")
    user_ref.set({"credits": initial_credits})
    logger.info("Test user setup completed")

    # --- Make the request ---
    logger.info(f"Making POST request to {BASE_URL}")
    response = app_client.post(BASE_URL, json=valid_payload)
    logger.info(f"Response status code: {response.status_code}")
    
    # --- Assertions ---
    # 1. Check API response
    logger.info("Checking API response...")
    assert response.status_code == 500
    logger.info("Response status is 500 (Internal Server Error)")
    
    response_text = response.get_data(as_text=True)
    logger.info(f"Response text: {response_text}")
    assert "credits have been refunded" in response_text
    logger.info("Error message verification passed")

    # 2. Verify data directly in Firestore
    logger.info("Verifying Firestore data...")
    
    # User's credits should be refunded to the original amount
    logger.info("Checking user credits were refunded...")
    user_snapshot = user_ref.get()
    assert user_snapshot.exists
    final_credits = user_snapshot.to_dict()["credits"]
    logger.info(f"Final credits: {final_credits} (should be {initial_credits})")
    assert final_credits == initial_credits
    logger.info("User credits verification passed - refund was successful")

    # Find the generation request to check its status
    logger.info("Checking generation request status...")
    requests_query = db.collection("generationRequests").where("userId", "==", valid_payload["userId"]).stream()
    request_list = list(requests_query)
    logger.info(f"Found {len(request_list)} generation requests")
    assert len(request_list) == 1
    gen_req_doc = request_list[0]
    
    # Generation request should be marked as 'failed'
    gen_req_data = gen_req_doc.to_dict()
    logger.info(f"Generation request data: {gen_req_data}")
    assert gen_req_data["status"] == "failed"
    logger.info("Generation request status verification passed - marked as 'failed'")

    # 3. Verify that both deduction and refund transactions were logged
    logger.info("Checking transaction history...")
    transactions = user_ref.collection("transactions").order_by("timestamp").stream()
    trans_list = list(transactions)
    logger.info(f"Found {len(trans_list)} transactions")
    assert len(trans_list) == 2
    logger.info("Transaction count verification passed")
    
    types = {t.to_dict()["type"] for t in trans_list}
    logger.info(f"Transaction types: {types}")
    assert "deduction" in types
    assert "refund" in types
    logger.info("Transaction types verification passed - both deduction and refund present")

    # Verify credit amounts in transactions
    logger.info("Verifying transaction amounts...")
    first_trans = trans_list[0].to_dict()
    second_trans = trans_list[1].to_dict()
    logger.info(f"First transaction: {first_trans}")
    logger.info(f"Second transaction: {second_trans}")
    
    assert first_trans["credits"] == 1 # deduction
    assert second_trans["credits"] == 1 # refund
    logger.info("Transaction amounts verification passed")
    
    logger.info("=== test_refund_on_ai_failure completed successfully ===")

logger.info("test_refund_on_failure module loaded successfully")