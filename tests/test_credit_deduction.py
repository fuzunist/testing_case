import logging
from unittest.mock import patch
import pytest
from firebase_admin import firestore

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_credit_deduction module ===")

@pytest.fixture
def valid_payload(managed_user):
    """
    Provides a valid payload for a generation request.
    It also ensures a user is created and cleaned up via the managed_user fixture.
    """
    logger.info("=== Setting up valid_payload fixture ===")
    user_id = managed_user("testUserSuccess", credits=100)
    payload = {
        "userId": user_id,
        "model": "Model A",
        "style": "anime",
        "color": "vibrant",
        "size": "1024x1024",  # Costs 3 credits
        "prompt": "A test prompt for credit deduction."
    }
    logger.info(f"Created valid payload for user '{user_id}': {payload}")
    return payload

@patch("functions.ai_simulator.AIChat.create")
def test_successful_credit_deduction(mock_ai_create, app_client, db, valid_payload):
    """
    Test successful credit deduction and record creation using the live emulator.
    This test relies on the managed_user fixture (via valid_payload) for setup/teardown.
    """
    logger.info("=== Starting test_successful_credit_deduction ===")
    logger.info(f"Test parameters: {valid_payload}")
    
    # --- Mock AI behavior ---
    mock_response = {
        "success": True,
        "imageUrl": "http://fake-url.com/image.png"
    }
    mock_ai_create.return_value = mock_response
    logger.info(f"Mocked AI response: {mock_response}")

    # --- Pre-check (Optional): Verify initial state ---
    logger.info("Verifying initial user state...")
    user_ref = db.collection("users").document(valid_payload["userId"])
    initial_credits = user_ref.get().to_dict()["credits"]
    logger.info(f"Initial credits for user '{valid_payload['userId']}': {initial_credits}")
    assert initial_credits == 100
    logger.info("Initial credit verification passed")

    # --- Make the request ---
    logger.info(f"Making POST request to {BASE_URL}")
    response = app_client.post(BASE_URL, json=valid_payload)
    logger.info(f"Response status code: {response.status_code}")
    
    # --- Assertions ---
    # 1. Check API response
    logger.info("Checking API response...")
    assert response.status_code == 200
    logger.info("Response status code is 200 (OK)")
    
    response_data = response.get_json()
    logger.info(f"Response data: {response_data}")
    
    assert response_data["deductedCredits"] == 3
    logger.info("Deducted credits verification passed")
    
    assert response_data["imageUrl"] == "http://fake-url.com/image.png"
    logger.info("Image URL verification passed")
    
    generation_id = response_data["generationRequestId"]
    logger.info(f"Generation request ID: {generation_id}")

    # 2. Verify data directly in Firestore
    logger.info("Verifying Firestore data...")
    
    # Check that user credits were debited
    logger.info("Checking user credit deduction...")
    user_snapshot = user_ref.get()
    assert user_snapshot.exists
    final_credits = user_snapshot.to_dict()["credits"]
    logger.info(f"Final credits for user '{valid_payload['userId']}': {final_credits}")
    assert final_credits == 97  # 100 - 3
    logger.info("User credit deduction verification passed")

    # Check that the generation request was created with the correct status
    logger.info("Checking generation request record...")
    gen_req_snapshot = db.collection("generationRequests").document(generation_id).get()
    assert gen_req_snapshot.exists
    gen_req_data = gen_req_snapshot.to_dict()
    logger.info(f"Generation request data: {gen_req_data}")
    
    assert gen_req_data["status"] == "completed"
    logger.info("Generation request status verification passed")
    
    assert gen_req_data["cost"] == 3
    logger.info("Generation request cost verification passed")
    
    assert gen_req_data["userId"] == valid_payload["userId"]
    logger.info("Generation request user ID verification passed")

    # 3. Verify the deduction transaction was logged
    logger.info("Checking transaction log...")
    transactions = user_ref.collection("transactions").stream()
    trans_list = list(transactions)
    logger.info(f"Found {len(trans_list)} transactions")
    
    assert len(trans_list) == 1
    logger.info("Transaction count verification passed")
    
    trans_data = trans_list[0].to_dict()
    logger.info(f"Transaction data: {trans_data}")
    
    assert trans_data["type"] == "deduction"
    logger.info("Transaction type verification passed")
    
    assert trans_data["credits"] == 3
    logger.info("Transaction credit amount verification passed")
    
    assert trans_data["generationRequestId"] == generation_id
    logger.info("Transaction generation request ID verification passed")
    
    logger.info("=== test_successful_credit_deduction completed successfully ===")

logger.info("test_credit_deduction module loaded successfully")