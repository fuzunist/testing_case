from unittest.mock import patch
import pytest
from firebase_admin import firestore

BASE_URL = "/createGenerationRequest"

@pytest.fixture
def valid_payload():
    """Provides a valid payload for a generation request."""
    return {
        "userId": "testUserRefund",
        "model": "Model B",
        "style": "sketch",
        "color": "monochrome",
        "size": "512x512", # Costs 1 credit
        "prompt": "A test prompt for refund logic."
    }

@patch("functions.ai_simulator.AIChat.create")
def test_refund_on_ai_failure(mock_ai_create, app_client, valid_payload):
    """
    Test that credits are refunded and status is 'failed' when AI generation fails.
    This is an integration test using the live emulator.
    """
    # --- Mock AI behavior to simulate a failure ---
    mock_ai_create.return_value = {
        "success": False,
        "error": "Simulated AI failure."
    }

    # --- Setup: Create the test user in Firestore ---
    db = firestore.client()
    user_ref = db.collection("users").document(valid_payload["userId"])
    initial_credits = 50
    user_ref.set({"credits": initial_credits})

    # --- Make the request ---
    response = app_client.post(BASE_URL, json=valid_payload)
    
    # --- Assertions ---
    # 1. Check API response
    assert response.status_code == 500
    assert "credits have been refunded" in response.get_data(as_text=True)

    # 2. Verify data directly in Firestore
    # User's credits should be refunded to the original amount
    user_snapshot = user_ref.get()
    assert user_snapshot.exists
    assert user_snapshot.to_dict()["credits"] == initial_credits

    # Find the generation request to check its status
    requests_query = db.collection("generationRequests").where("userId", "==", valid_payload["userId"]).stream()
    request_list = list(requests_query)
    assert len(request_list) == 1
    gen_req_doc = request_list[0]
    
    # Generation request should be marked as 'failed'
    assert gen_req_doc.to_dict()["status"] == "failed"

    # 3. Verify that both deduction and refund transactions were logged
    transactions = user_ref.collection("transactions").order_by("timestamp").stream()
    trans_list = list(transactions)
    assert len(trans_list) == 2
    
    types = {t.to_dict()["type"] for t in trans_list}
    assert "deduction" in types
    assert "refund" in types

    # Verify credit amounts in transactions
    assert trans_list[0].to_dict()["credits"] == 1 # deduction
    assert trans_list[1].to_dict()["credits"] == 1 # refund