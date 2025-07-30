import pytest
import requests
from unittest.mock import patch
import sys
import os

# Add functions directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'functions'))


def test_refund_on_generation_failure(api_base_url, firestore_client):
    """Test that credits are refunded when AI generation fails"""
    
    # Mock the AI simulator to always fail
    with patch('functions.main.simulate_generation') as mock_simulate:
        mock_simulate.return_value = {
            "success": False,
            "error": "Simulated generation failure"
        }
        
        initial_credits = 100
        
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": "1024x1024",
            "prompt": "This should fail and trigger refund"
        }
        
        response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        # Should return 500 error for generation failure
        assert response.status_code == 500
        assert "AI generation failed, credits have been refunded" in response.json()["error"]
        
        # Verify credits were refunded (should be back to original amount)
        user_doc = firestore_client.collection('users').document('testUser1').get()
        user_data = user_doc.to_dict()
        assert user_data['credits'] == initial_credits
        
        # Verify there are both deduction and refund transactions
        transactions = list(
            firestore_client.collection('users')
            .document('testUser1')
            .collection('transactions')
            .stream()
        )
        
        assert len(transactions) == 2  # One deduction, one refund
        
        # Find deduction and refund transactions
        deduction_transaction = None
        refund_transaction = None
        
        for transaction in transactions:
            data = transaction.to_dict()
            if data['type'] == 'deduction':
                deduction_transaction = data
            elif data['type'] == 'refund':
                refund_transaction = data
        
        assert deduction_transaction is not None
        assert refund_transaction is not None
        
        # Verify transaction details
        assert deduction_transaction['credits'] == 3  # 1024x1024 costs 3 credits
        assert refund_transaction['credits'] == 3
        assert refund_transaction['generationRequestId'] is not None
        
        # Verify generation request status is 'failed'
        request_id = refund_transaction['generationRequestId']
        request_doc = firestore_client.collection('generationRequests').document(request_id).get()
        request_data = request_doc.to_dict()
        assert request_data['status'] == 'failed'


def test_multiple_failures_with_refunds(api_base_url, firestore_client):
    """Test multiple generation failures and verify all refunds work correctly"""
    
    with patch('functions.main.simulate_generation') as mock_simulate:
        mock_simulate.return_value = {
            "success": False,
            "error": "Simulated generation failure"
        }
        
        initial_credits = 100
        
        # Make multiple requests that will all fail
        requests_data = [
            {"size": "512x512", "cost": 1},
            {"size": "1024x1024", "cost": 3},
            {"size": "1024x1792", "cost": 4},
        ]
        
        for i, req_data in enumerate(requests_data):
            payload = {
                "userId": "testUser1",
                "model": "Model A",
                "style": "realistic",
                "color": "vibrant",
                "size": req_data["size"],
                "prompt": f"Failed request {i+1}"
            }
            
            response = requests.post(
                f"{api_base_url}/createGenerationRequest",
                json=payload
            )
            
            assert response.status_code == 500
        
        # Verify credits are still at initial amount after all refunds
        user_doc = firestore_client.collection('users').document('testUser1').get()
        user_data = user_doc.to_dict()
        assert user_data['credits'] == initial_credits
        
        # Verify we have correct number of transactions (3 deductions + 3 refunds)
        transactions = list(
            firestore_client.collection('users')
            .document('testUser1')
            .collection('transactions')
            .stream()
        )
        assert len(transactions) == 6


def test_partial_success_scenario(api_base_url, firestore_client):
    """Test scenario where some requests succeed and some fail"""
    
    success_count = 0
    
    def mock_generation(model):
        nonlocal success_count
        success_count += 1
        
        # First request succeeds, second fails
        if success_count == 1:
            return {
                "success": True,
                "imageUrl": "https://example.com/success.jpg"
            }
        else:
            return {
                "success": False,
                "error": "Simulated generation failure"
            }
    
    with patch('functions.main.simulate_generation') as mock_simulate:
        mock_simulate.side_effect = mock_generation
        
        initial_credits = 100
        
        # First request - should succeed
        payload1 = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": "1024x1024",  # 3 credits
            "prompt": "This should succeed"
        }
        
        response1 = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload1
        )
        
        assert response1.status_code == 201
        
        # Check credits after first request
        user_doc = firestore_client.collection('users').document('testUser1').get()
        assert user_doc.to_dict()['credits'] == 97  # 100 - 3 = 97
        
        # Second request - should fail and refund
        payload2 = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": "512x512",  # 1 credit
            "prompt": "This should fail and refund"
        }
        
        response2 = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload2
        )
        
        assert response2.status_code == 500
        
        # Check final credits - should be back to 97 (first success remains deducted)
        user_doc = firestore_client.collection('users').document('testUser1').get()
        assert user_doc.to_dict()['credits'] == 97  # Refund of 1 credit from failed request