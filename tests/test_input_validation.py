import pytest

BASE_URL = "/createGenerationRequest"

def test_missing_required_fields(app_client):
    """
    Test that the API correctly rejects requests with missing fields.
    """
    incomplete_payloads = [
        {"model": "Model A", "style": "anime", "color": "vibrant", "size": "512x512"},
        {"userId": "user1", "style": "anime", "color": "vibrant", "size": "512x512"},
        {"userId": "user1", "model": "Model A", "color": "vibrant", "size": "512x512"},
        {"userId": "user1", "model": "Model A", "style": "anime", "size": "512x512"},
        {"userId": "user1", "model": "Model A", "style": "anime", "color": "vibrant"}
    ]
    
    for payload in incomplete_payloads:
        response = app_client.post(BASE_URL, json=payload)
        assert response.status_code == 400
        assert "Missing required fields" in response.get_data(as_text=True)

def test_invalid_enum_values(app_client):
    """
    Test that the API rejects requests with invalid enum-like values
    (model, style, color, size).
    """
    base_payload = {
        "userId": "user1", "model": "Model A", "style": "anime", 
        "color": "vibrant", "size": "512x512", "prompt": "test"
    }
    
    invalid_payloads = [
        {**base_payload, "model": "Invalid Model"},
        {**base_payload, "style": "Invalid Style"},
        {**base_payload, "color": "Invalid Color"},
        {**base_payload, "size": "Invalid Size"}
    ]
    
    for payload in invalid_payloads:
        response = app_client.post(BASE_URL, json=payload)
        assert response.status_code == 400
        if "model" in payload and payload["model"] == "Invalid Model":
            assert "Invalid model" in response.get_data(as_text=True)
        else:
            assert "Invalid style, color, or size" in response.get_data(as_text=True)