from unittest.mock import patch
import pytest
from firebase_admin import firestore
from datetime import datetime, timezone

BASE_URL = "/getUserCredits"

def test_get_user_credits_success(app_client):
    """
    Test successful retrieval of a user's credits and transaction history
    using the live emulator. This is an integration test.
    """
    # --- Setup: Create a user with a transaction history in Firestore ---
    db = firestore.client()
    user_id = "userWithHistory"
    user_ref = db.collection("users").document(user_id)
    
    # Set initial credits
    user_ref.set({"credits": 97})
    
    # Create transaction records
    trans_ref = user_ref.collection("transactions")
    trans_ref.document("t1").set({
        "type": "deduction",
        "credits": 5,
        "generationRequestId": "gen1",
        "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    })
    trans_ref.document("t2").set({
        "type": "refund",
        "credits": 2,
        "generationRequestId": "gen2",
        "timestamp": datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    })
    trans_ref.document("t3").set({ # Another deduction
        "type": "deduction",
        "credits": 0, # freebie
        "generationRequestId": "gen3",
        "timestamp": datetime(2023, 1, 3, 12, 0, 0, tzinfo=timezone.utc)
    })

    # --- Make the request ---
    response = app_client.get(f"{BASE_URL}?userId={user_id}")

    # --- Assertions ---
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify current credits
    assert data["currentCredits"] == 97
    
    # Verify transaction history
    transactions = data["transactions"]
    assert len(transactions) == 3
    
    # Transactions should be sorted by timestamp descending
    assert transactions[0]["id"] == "t3"
    assert transactions[0]["type"] == "deduction"
    assert transactions[1]["id"] == "t2"
    assert transactions[1]["type"] == "refund"
    assert transactions[1]["credits"] == 2
    assert transactions[2]["id"] == "t1"
    assert transactions[2]["type"] == "deduction"
    assert "timestamp" in transactions[0]


def test_get_user_credits_not_found(app_client):
    """
    Test the response for a non-existent user using the live emulator.
    """
    user_id = "nonExistentUser"
    
    response = app_client.get(f"{BASE_URL}?userId={user_id}")
    
    assert response.status_code == 404
    assert "User not found" in response.get_data(as_text=True)

def test_get_user_credits_missing_userid(app_client):
    """
    Test the response when the userId parameter is missing.
    """
    response = app_client.get(BASE_URL)
    
    assert response.status_code == 400
    assert "userId parameter is required" in response.get_data(as_text=True)