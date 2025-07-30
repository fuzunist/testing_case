import pytest
import requests


def test_insufficient_funds_exact_limit(api_base_url, firestore_client):
    """Test that testUser2 (10 credits) can make exactly enough requests before failing"""
    
    # First request: 1024x1792 = 4 credits (should succeed, leaving 6 credits)
    payload1 = {
        "userId": "testUser2",
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "1024x1792",
        "prompt": "First image"
    }
    
    response1 = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload1
    )
    
    assert response1.status_code == 201
    
    # Verify credits deducted
    user_doc = firestore_client.collection('users').document('testUser2').get()
    assert user_doc.to_dict()['credits'] == 6
    
    # Second request: 1024x1024 = 3 credits (should succeed, leaving 3 credits)
    payload2 = {
        "userId": "testUser2",
        "model": "Model B",
        "style": "anime",
        "color": "neon",
        "size": "1024x1024",
        "prompt": "Second image"
    }
    
    response2 = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload2
    )
    
    assert response2.status_code == 201
    
    # Verify credits deducted
    user_doc = firestore_client.collection('users').document('testUser2').get()
    assert user_doc.to_dict()['credits'] == 3
    
    # Third request: 1024x1792 = 4 credits (should fail - insufficient funds)
    payload3 = {
        "userId": "testUser2",
        "model": "Model A",
        "style": "sketch",
        "color": "monochrome",
        "size": "1024x1792",
        "prompt": "Third image that should fail"
    }
    
    response3 = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload3
    )
    
    assert response3.status_code == 402
    assert "Insufficient credits" in response3.json()["error"]
    
    # Verify credits unchanged
    user_doc = firestore_client.collection('users').document('testUser2').get()
    assert user_doc.to_dict()['credits'] == 3  # Should remain unchanged


def test_insufficient_funds_single_request(api_base_url, firestore_client):
    """Test that a user with 10 credits cannot make a request that costs more than available"""
    
    # Set user to have only 2 credits
    firestore_client.collection('users').document('testUser2').set({'credits': 2})
    
    # Try to make a 1024x1024 request (3 credits) - should fail
    payload = {
        "userId": "testUser2",
        "model": "Model A",
        "style": "cyberpunk",
        "color": "neon",
        "size": "1024x1024",
        "prompt": "Should fail due to insufficient credits"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 402
    assert "Insufficient credits" in response.json()["error"]
    
    # Verify credits unchanged
    user_doc = firestore_client.collection('users').document('testUser2').get()
    assert user_doc.to_dict()['credits'] == 2


def test_multiple_small_requests_until_exhaustion(api_base_url, firestore_client):
    """Test multiple small requests until credits are exhausted"""
    
    # Make 10 requests of 512x512 (1 credit each) - should all succeed
    for i in range(10):
        payload = {
            "userId": "testUser2",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": "512x512",
            "prompt": f"Image {i+1}"
        }
        
        response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        assert response.status_code == 201
    
    # Verify all credits exhausted
    user_doc = firestore_client.collection('users').document('testUser2').get()
    assert user_doc.to_dict()['credits'] == 0
    
    # 11th request should fail
    payload_fail = {
        "userId": "testUser2",
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "512x512",
        "prompt": "This should fail"
    }
    
    response_fail = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload_fail
    )
    
    assert response_fail.status_code == 402
    assert "Insufficient credits" in response_fail.json()["error"]