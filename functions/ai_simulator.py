import random
from enum import Enum


class ImageModels(Enum):
    """
    Enumeration for the available AI models.
    """
    model_a = "Model A"
    model_b = "Model B"


class AIChat:
    """
    Simulates an AI model for image generation with a configurable failure rate.
    """
    
    def __init__(self, model: ImageModels, failure_rate: float = 0.05):
        """
        Initializes the simulator with a specific model and failure rate.
        
        Args:
            model: The AI model to simulate (ImageModels.model_a or ImageModels.model_b).
            failure_rate: The probability of generation failure (0.0 to 1.0).
        """
        if not isinstance(model, ImageModels):
            raise TypeError("model must be an instance of ImageModels Enum")
        
        self.model = model
        self.failure_rate = failure_rate
        self.placeholder_urls = {
            ImageModels.model_a: "https://storage.googleapis.com/proudcity/mebanenc/uploads/2018/02/placeholder-image.png",
            ImageModels.model_b: "https://www.russorizio.com/wp-content/uploads/2016/07/ef3-placeholder-image.jpg"
        }

    def create(self):
        """
        Simulates the image generation process.
        
        Returns:
            A dictionary containing the success status and the image URL or an error message.
        """
        if random.random() < self.failure_rate:
            return {
                "success": False,
                "error": "AI generation failed due to a simulated error."
            }
        
        return {
            "success": True,
            "imageUrl": self.placeholder_urls[self.model]
        }