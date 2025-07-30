import pytest
import requests


def test_invalid_style(api_base_url):
    """Test validation of invalid style parameter"""
    
    payload = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "invalid_style",  # Invalid style
        "color": "vibrant",
        "size": "1024x1024",
        "prompt": "Test prompt"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 400
    assert "Invalid style" in response.json()["error"]


def test_invalid_color(api_base_url):
    """Test validation of invalid color parameter"""
    
    payload = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "realistic",
        "color": "invalid_color",  # Invalid color
        "size": "1024x1024",
        "prompt": "Test prompt"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 400
    assert "Invalid color" in response.json()["error"]


def test_invalid_size(api_base_url):
    """Test validation of invalid size parameter"""
    
    payload = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "invalid_size",  # Invalid size
        "prompt": "Test prompt"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 400
    assert "Invalid size" in response.json()["error"]


def test_invalid_model(api_base_url):
    """Test validation of invalid model parameter"""
    
    payload = {
        "userId": "testUser1",
        "model": "Model C",  # Invalid model
        "style": "realistic",
        "color": "vibrant",
        "size": "1024x1024",
        "prompt": "Test prompt"
    }
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload
    )
    
    assert response.status_code == 400
    assert "Invalid model" in response.json()["error"]


def test_missing_required_fields(api_base_url):
    """Test validation when required fields are missing"""
    
    # Missing userId
    payload1 = {
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "1024x1024",
        "prompt": "Test prompt"
    }
    
    response1 = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload1
    )
    
    assert response1.status_code == 400
    assert "Missing required fields" in response1.json()["error"]
    
    # Missing prompt
    payload2 = {
        "userId": "testUser1",
        "model": "Model A",
        "style": "realistic",
        "color": "vibrant",
        "size": "1024x1024"
    }
    
    response2 = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json=payload2
    )
    
    assert response2.status_code == 400
    assert "Missing required fields" in response2.json()["error"]


def test_empty_json_payload(api_base_url):
    """Test handling of empty JSON payload"""
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        json={}
    )
    
    assert response.status_code == 400
    assert "Missing required fields" in response.json()["error"]


def test_invalid_json_payload(api_base_url):
    """Test handling of invalid JSON"""
    
    response = requests.post(
        f"{api_base_url}/createGenerationRequest",
        data="invalid json",
        headers={'Content-Type': 'application/json'}
    )
    
    assert response.status_code == 400
    assert "Invalid JSON payload" in response.json()["error"]


def test_wrong_http_method(api_base_url):
    """Test that only POST method is accepted for createGenerationRequest"""
    
    # Try GET method
    response_get = requests.get(f"{api_base_url}/createGenerationRequest")
    assert response_get.status_code == 405
    assert "Method not allowed" in response_get.json()["error"]
    
    # Try PUT method
    response_put = requests.put(f"{api_base_url}/createGenerationRequest")
    assert response_put.status_code == 405
    assert "Method not allowed" in response_put.json()["error"]


def test_valid_style_values(api_base_url):
    """Test all valid style values"""
    
    valid_styles = ['realistic', 'anime', 'oil painting', 'sketch', 'cyberpunk', 'watercolor']
    
    for style in valid_styles:
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": style,
            "color": "vibrant",
            "size": "512x512",
            "prompt": f"Test {style} style"
        }
        
        response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        # Should succeed (201) or fail for other reasons but not validation (not 400)
        assert response.status_code != 400, f"Style '{style}' should be valid"


def test_valid_color_values(api_base_url):
    """Test all valid color values"""
    
    valid_colors = ['vibrant', 'monochrome', 'pastel', 'neon', 'vintage']
    
    for color in valid_colors:
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": color,
            "size": "512x512",
            "prompt": f"Test {color} color"
        }
        
        response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        # Should succeed (201) or fail for other reasons but not validation (not 400)
        assert response.status_code != 400, f"Color '{color}' should be valid"


def test_valid_size_values(api_base_url):
    """Test all valid size values"""
    
    valid_sizes = ['512x512', '1024x1024', '1024x1792']
    
    for size in valid_sizes:
        payload = {
            "userId": "testUser1",
            "model": "Model A",
            "style": "realistic",
            "color": "vibrant",
            "size": size,
            "prompt": f"Test {size} size"
        }
        
        response = requests.post(
            f"{api_base_url}/createGenerationRequest",
            json=payload
        )
        
        # Should succeed (201) or fail for other reasons but not validation (not 400)
        assert response.status_code != 400, f"Size '{size}' should be valid"