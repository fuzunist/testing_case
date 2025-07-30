import pytest
import requests
import json


def test_credit_deduction_1024x1024(api_base_url, firestore_client):
    """Test credit deduction for 1024x1024 image (3 credits)"""
    
    # Make generation request
    payload = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "1024x1024",
        "prompt": "A beautiful landscape"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    # Verify successful response
    assert response.status_code == 201
    response_data = response.json()
    
    assert "generationRequestId" in response_data
    assert response_data["deductedCredits"] == 3
    assert "imageUrl" in response_data
    
    # Verify user's credit balance
    user_doc = firestore_client.collection('users').document('testUser1').get()
    user_data = user_doc.to_dict()
    assert user_data['credits'] == 97  # 100 - 3 = 97
    
    # Verify transaction record
    transactions = list(firestore_client.collection('users').document('testUser1').collection('transactions').stream())
    assert len(transactions) == 1
    
    transaction_data = transactions[0].to_dict()
    assert transaction_data['type'] == 'deduction'
    assert transaction_data['credits'] == 3
    assert transaction_data['generationRequestId'] == response_data["generationRequestId"]


def test_credit_deduction_512x512(api_base_url, firestore_client):
    """Test credit deduction for 512x512 image (1 credit)"""
    
    payload = {
        "userId": "testUser1",
        "model": "Model B",
        "style": "anime",
        "color": "neon",
        "size": "512x512",
        "prompt": "An anime character"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["deductedCredits"] == 1
    
    # Verify user's credit balance
    user_doc = firestore_client.collection('users').document('testUser1').get()
    user_data = user_doc.to_dict()
    assert user_data['credits'] == 99  # 100 - 1 = 99


def test_credit_deduction_1024x1792(api_base_url, firestore_client):
    """Test credit deduction for 1024x1792 image (4 credits)"""
    
    payload = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "oil painting",
        "color": "vintage",
        "size": "1024x1792",
        "prompt": "A vintage oil painting"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["deductedCredits"] == 4
    
    # Verify user's credit balance
    user_doc = firestore_client.collection('users').document('testUser1').get()
    user_data = user_doc.to_dict()
    assert user_data['credits'] == 96  # 100 - 4 = 96