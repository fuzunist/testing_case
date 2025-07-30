import random
from typing import Dict, Any


def simulate_generation(model: str) -> Dict[str, Any]:
    """
    Simulates AI image generation for Model A or Model B.
    
    Args:
        model: The AI model to simulate ("Model A" or "Model B")
        
    Returns:
        Dictionary with success status and either imageUrl or error message
    """
    # 5% failure rate simulation
    if random.random() < 0.05:
        return {
            "success": False,
            "error": "Simulated generation failure"
        }
    
    # Success case - return appropriate placeholder URL for each model
    if model == "Model A":
        return {
            "success": True,
            "imageUrl": "https://storage.googleapis.com/ai-image-gen-backend.appspot.com/placeholders/model_a_placeholder.jpg"
        }
    elif model == "Model B":
        return {
            "success": True,
            "imageUrl": "https://storage.googleapis.com/ai-image-gen-backend.appspot.com/placeholders/model_b_placeholder.jpg"
        }
    else:
        return {
            "success": False,
            "error": f"Unknown model: {model}"
        }