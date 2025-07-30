from unittest.mock import patch
import pytest
from firebase_admin import firestore

BASE_URL = "/createGenerationRequest"

@pytest.fixture
def valid_payload():
    """Provides a valid payload for a generation request."""
    return {
        "userId": "testUser1",
        "model": "Model A",
        "style": "anime",
        "color": "vibrant",
        "size": "1024x1024", # Costs 3 credits
        "prompt": "A test prompt for credit deduction."
    }

@patch("functions.ai_simulator.AIChat.create")
def test_successful_credit_deduction(mock_ai_create, app_client, valid_payload):
    """
    Test successful credit deduction and record creation using the live emulator.
    This is now an integration test.
    """
    # --- Mock AI behavior (we still mock the AI to control test outcomes) ---
    mock_ai_create.return_value = {
        "success": True,
        "imageUrl": "http://fake-url.com/image.png"
    }

    # --- Setup: Create the test user directly in the emulator's Firestore ---
    db = firestore.client()
    user_ref = db.collection("users").document(valid_payload["userId"])
    user_ref.set({"credits": 100})

    # --- Make the request ---
    response = app_client.post(BASE_URL, json=valid_payload)
    
    # --- Assertions ---
    # 1. Check API response
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["deductedCredits"] == 3
    assert response_data["imageUrl"] == "http://fake-url.com/image.png"
    generation_id = response_data["generationRequestId"]

    # 2. Verify data directly in Firestore
    # Check that user credits were debited
    user_snapshot = user_ref.get()
    assert user_snapshot.exists
    assert user_snapshot.to_dict()["credits"] == 97 # 100 - 3

    # Check that the generation request was created with the correct status
    gen_req_snapshot = db.collection("generationRequests").document(generation_id).get()
    assert gen_req_snapshot.exists
    gen_req_data = gen_req_snapshot.to_dict()
    assert gen_req_data["status"] == "completed"
    assert gen_req_data["cost"] == 3
    assert gen_req_data["userId"] == valid_payload["userId"]

    # 3. Verify the deduction transaction was logged
    transactions = user_ref.collection("transactions").stream()
    trans_list = list(transactions)
    assert len(trans_list) == 1
    trans_data = trans_list[0].to_dict()
    assert trans_data["type"] == "deduction"
    assert trans_data["credits"] == 3
    assert trans_data["generationRequestId"] == generation_id