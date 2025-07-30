import pytest
import requests


def test_get_user_credits_initial_state(api_base_url, firestore_client):
    """Test getting user credits in initial state"""
    
    response = requests.get(f"{api_base_url}/getUserCredits?userId=testUser1")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["currentCredits"] == 100
    assert data["transactions"] == []  # No transactions initially


def test_get_user_credits_after_transactions(api_base_url, firestore_client):
    """Test getting user credits after making transactions"""
    
    # Make a generation request first
    payload = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "1024x1024",
        "prompt": "Test image"
    }
    
    gen_response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert gen_response.status_code == 201
    generation_request_id = gen_response.json()["generationRequestId"]
    
    # Now get user credits
    response = requests.get(f"{api_base_url}/getUserCredits?userId=testUser1")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["currentCredits"] == 97  # 100 - 3 = 97
    assert len(data["transactions"]) == 1
    
    transaction = data["transactions"][0]
    assert transaction["type"] == "deduction"
    assert transaction["credits"] == 3
    assert transaction["generationRequestId"] == generation_request_id
    assert "timestamp" in transaction
    assert "id" in transaction


def test_get_user_credits_multiple_transactions(api_base_url, firestore_client):
    """Test getting user credits with multiple transactions"""
    
    # Make multiple generation requests
    requests_data = [
        {"size": "512x512", "cost": 1},
        {"size": "1024x1024", "cost": 3},
        {"size": "1024x1792", "cost": 4}
    ]
    
    for i, req_data in enumerate(requests_data):
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": req_data["size"],
            "prompt": f"Test image {i+1}"
        }
        
        gen_response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        assert gen_response.status_code == 201
    
    # Get user credits
    response = requests.get(f"{api_base_url}/getUserCredits?userId=testUser1")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have spent 1 + 3 + 4 = 8 credits
    assert data["currentCredits"] == 92  # 100 - 8 = 92
    assert len(data["transactions"]) == 3
    
    # Verify all transactions are present
    transaction_costs = [t["credits"] for t in data["transactions"]]
    assert sorted(transaction_costs) == [1, 3, 4]
    
    # Verify all are deduction transactions
    for transaction in data["transactions"]:
        assert transaction["type"] == "deduction"
        assert "generationRequestId" in transaction


def test_get_user_credits_with_refunds(api_base_url, firestore_client):
    """Test getting user credits when there are refund transactions"""
    
    from unittest.mock import patch
    
    # Mock one failure to create refund transaction
    with patch('functions.main.simulate_generation') as mock_simulate:
        mock_simulate.return_value = {
            "success": False,
            "error": "Simulated generation failure"
        }
        
        # Make a request that will fail and be refunded
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": "1024x1024",
            "prompt": "This will fail"
        }
        
        gen_response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        assert gen_response.status_code == 500  # Should fail
    
    # Get user credits
    response = requests.get(f"{api_base_url}/getUserCredits?userId=testUser1")
    
    assert response.status_code == 200
    data = response.json()
    
    # Credits should be back to 100 after refund
    assert data["currentCredits"] == 100
    assert len(data["transactions"]) == 2  # One deduction, one refund
    
    # Find deduction and refund transactions
    deduction_transactions = [t for t in data["transactions"] if t["type"] == "deduction"]
    refund_transactions = [t for t in data["transactions"] if t["type"] == "refund"]
    
    assert len(deduction_transactions) == 1
    assert len(refund_transactions) == 1
    
    assert deduction_transactions[0]["credits"] == 3
    assert refund_transactions[0]["credits"] == 3


def test_get_user_credits_nonexistent_user(api_base_url):
    """Test getting credits for a user that doesn't exist"""
    
    response = requests.get(f"{api_base_url}/getUserCredits?userId=nonexistentUser")
    
    assert response.status_code == 404
    assert "User not found" in response.json()["error"]


def test_get_user_credits_missing_user_id(api_base_url):
    """Test getting credits without providing userId parameter"""
    
    response = requests.get(f"{api_base_url}/getUserCredits")
    
    assert response.status_code == 400
    assert "Missing userId parameter" in response.json()["error"]


def test_get_user_credits_wrong_method(api_base_url):
    """Test that only GET method is accepted for getUserCredits"""
    
    # Try POST method
    response_post = requests.post(f"{api_base_url}/getUserCredits?userId=testUser1")
    assert response_post.status_code == 405
    assert "Method not allowed" in response_post.json()["error"]
    
    # Try PUT method
    response_put = requests.put(f"{api_base_url}/getUserCredits?userId=testUser1")
    assert response_put.status_code == 405
    assert "Method not allowed" in response_put.json()["error"]


def test_get_user_credits_transaction_ordering(api_base_url, firestore_client):
    """Test that transactions are returned in descending order by timestamp"""
    
    import time
    
    # Make multiple requests with small delays to ensure different timestamps
    for i in range(3):
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": "512x512",
            "prompt": f"Test image {i+1}"
        }
        
        requests.post(f"{api_base_url}/createGenerationRequest", json=payload)
        time.sleep(0.1)  # Small delay
    
    # Get user credits
    response = requests.get(f"{api_base_url}/getUserCredits?userId=testUser1")
    
    assert response.status_code == 200
    data = response.json()
    
    transactions = data["transactions"]
    assert len(transactions) == 3
    
    # Verify timestamps are in descending order (most recent first)
    timestamps = [t["timestamp"] for t in transactions]
    # Convert to comparable format and check order
    for i in range(len(timestamps) - 1):
        # Most recent should come first
        assert timestamps[i] >= timestamps[i + 1] or abs(timestamps[i] - timestamps[i + 1]) < 1


def test_get_user_credits_testuser2(api_base_url):
    """Test getting credits for testUser2 (different initial balance)"""
    
    response = requests.get(f"{api_base_url}/getUserCredits?userId=testUser2")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["currentCredits"] == 10  # testUser2 starts with 10 credits
    assert data["transactions"] == []