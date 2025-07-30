from unittest.mock import patch
import pytest
from firebase_admin import firestore

BASE_URL = "/createGenerationRequest"

@pytest.fixture
def expensive_payload():
    """Provides a payload that costs more credits than the user has."""
    return {
        "userId": "testUserInsufficient",
        "model": "Model B",
        "style": "cyberpunk",
        "color": "neon",
        "size": "1024x1792", # Costs 4 credits
        "prompt": "A cyberpunk city in neon colors."
    }

def test_insufficient_credits_rejection(app_client, expensive_payload):
    """
    Test that a request from a user with insufficient credits is rejected
    and no database changes are made. This is an integration test.
    """
    # --- Setup: Create a user with insufficient credits in Firestore ---
    db = firestore.client()
    user_ref = db.collection("users").document(expensive_payload["userId"])
    initial_credits = 2 # Cost is 4, user only has 2
    user_ref.set({"credits": initial_credits})

    # --- Make the request ---
    response = app_client.post(BASE_URL, json=expensive_payload)
    
    # --- Assertions ---
    # 1. Check API response for the correct error
    assert response.status_code == 412 # FAILED_PRECONDITION
    assert "Insufficient credits" in response.get_data(as_text=True)

    # 2. Verify that no data was changed in Firestore
    # User credits should remain unchanged
    user_snapshot = user_ref.get()
    assert user_snapshot.to_dict()["credits"] == initial_credits

    # No generation request should have been created
    requests_query = db.collection("generationRequests").where("userId", "==", expensive_payload["userId"]).stream()
    assert len(list(requests_query)) == 0

    # No transactions should have been logged
    transactions_query = user_ref.collection("transactions").stream()
    assert len(list(transactions_query)) == 0