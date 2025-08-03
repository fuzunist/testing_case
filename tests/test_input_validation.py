import logging
import pytest

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_input_validation module ===")

def test_missing_required_fields(app_client):
    """
    Test that the API correctly rejects requests with missing fields.
    """
    logger.info("=== Starting test_missing_required_fields ===")
    
    incomplete_payloads = [
        {"model": "model-a", "style": "anime", "color": "vibrant", "size": "512x512"},
        {"userId": "user1", "style": "anime", "color": "vibrant", "size": "512x512"},
        {"userId": "user1", "model": "model-a", "color": "vibrant", "size": "512x512"},
        {"userId": "user1", "model": "model-a", "style": "anime", "size": "512x512"},
        {"userId": "user1", "model": "model-a", "style": "anime", "color": "vibrant"}
    ]
    
    logger.info(f"Testing {len(incomplete_payloads)} incomplete payloads")
    
    for i, payload in enumerate(incomplete_payloads, 1):
        logger.info(f"Testing payload {i}: {payload}")
        
        logger.info(f"Making POST request to {BASE_URL}")
        response = app_client.post(BASE_URL, json=payload)
        logger.info(f"Response status code: {response.status_code}")
        
        logger.info("Checking response...")
        assert response.status_code == 400
        logger.info("Response status is 400 (Bad Request)")
        
        response_text = response.get_data(as_text=True)
        logger.info(f"Response text: {response_text}")
        assert "Missing required fields" in response_text
        logger.info(f"Payload {i} validation passed - correctly rejected missing fields")
    
    logger.info("=== test_missing_required_fields completed successfully ===")

def test_invalid_enum_values(app_client):
    """
    Test that the API rejects requests with invalid enum-like values
    (model, style, color, size).
    """
    logger.info("=== Starting test_invalid_enum_values ===")
    
    base_payload = {
        "userId": "user1", "model": "model-a", "style": "anime", 
        "color": "vibrant", "size": "512x512", "prompt": "test"
    }
    
    logger.info(f"Base payload: {base_payload}")
    
    invalid_payloads = [
        {**base_payload, "model": "Invalid Model"},
        {**base_payload, "style": "Invalid Style"},
        {**base_payload, "color": "Invalid Color"},
        {**base_payload, "size": "Invalid Size"}
    ]
    
    logger.info(f"Testing {len(invalid_payloads)} invalid enum value payloads")
    
    for i, payload in enumerate(invalid_payloads, 1):
        logger.info(f"Testing payload {i}: {payload}")
        
        logger.info(f"Making POST request to {BASE_URL}")
        response = app_client.post(BASE_URL, json=payload)
        logger.info(f"Response status code: {response.status_code}")
        
        logger.info("Checking response...")
        assert response.status_code == 400
        logger.info("Response status is 400 (Bad Request)")
        
        response_text = response.get_data(as_text=True)
        logger.info(f"Response text: {response_text}")
        
        if "model" in payload and payload["model"] == "Invalid Model":
            assert "Invalid model" in response_text
            logger.info(f"Payload {i} validation passed - correctly rejected invalid model")
        else:
            assert "Invalid style, color, or size" in response_text
            logger.info(f"Payload {i} validation passed - correctly rejected invalid enum value")
    
    logger.info("=== test_invalid_enum_values completed successfully ===")

logger.info("test_input_validation module loaded successfully")