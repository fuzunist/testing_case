import random
import logging
from config import ImageModels, AIModelsConfig

# Configure logging for AI simulator module
logger = logging.getLogger(__name__)

logger.info("Initializing AI Simulator module...")


class AIChat:
    """
    Simulates an AI model for image generation with a configurable failure rate.
    """
    
    def __init__(self, model: ImageModels, failure_rate: float = AIModelsConfig.DEFAULT_FAILURE_RATE):
        """
        Initializes the simulator with a specific model and failure rate.
        
        Args:
            model: The AI model to simulate (ImageModels.model_a or ImageModels.model_b).
            failure_rate: The probability of generation failure (0.0 to 1.0).
        """
        logger.info(f"=== Initializing AIChat simulator ===")
        logger.info(f"Model: {model.value}")
        logger.info(f"Failure rate: {failure_rate}")
        
        # Validate model - accept both enum and string values
        if hasattr(model, 'value'):
            model_value = model.value
        else:
            model_value = str(model)
        
        valid_model_values = ["model-a", "model-b"]
        if model_value not in valid_model_values:
            logger.error(f"Invalid model value: {model_value}. Expected one of: {valid_model_values}")
            raise TypeError(f"model must be one of: {valid_model_values}")
        
        # Store the actual enum if possible, otherwise create it
        if hasattr(model, 'value'):
            self.model = model
        else:
            # Convert string to enum
            from config import ImageModels
            if model_value == "model-a":
                self.model = ImageModels.model_a
            elif model_value == "model-b":
                self.model = ImageModels.model_b
        
        if not 0.0 <= failure_rate <= 1.0:
            logger.warning(f"Failure rate {failure_rate} is outside valid range [0.0, 1.0]. Clamping to valid range.")
            failure_rate = max(0.0, min(1.0, failure_rate))
        
        # self.model is set above in validation
        self.failure_rate = failure_rate
        self.placeholder_urls = AIModelsConfig.PLACEHOLDER_URLS
        
        logger.info(f"AIChat simulator initialized successfully for {model.value}")
        logger.debug(f"Available placeholder URLs: {list(self.placeholder_urls.keys())}")

    def create(self):
        """
        Simulates the image generation process.
        
        Returns:
            A dictionary containing the success status and the image URL or an error message.
        """
        logger.info(f"=== Starting AI image generation ===")
        logger.info(f"Model: {self.model.value}")
        logger.info(f"Failure rate: {self.failure_rate}")
        
        # Generate random number for failure simulation
        random_value = random.random()
        logger.debug(f"Random value generated: {random_value}")
        
        if random_value < self.failure_rate:
            logger.warning(f"AI generation failed for model {self.model.value}")
            logger.debug(f"Random value {random_value} < failure rate {self.failure_rate}")
            
            error_result = {
                "success": False,
                "error": "AI generation failed due to a simulated error."
            }
            logger.info(f"Returning failure result: {error_result}")
            return error_result
        
        logger.info(f"AI generation successful for model {self.model.value}")
        logger.debug(f"Random value {random_value} >= failure rate {self.failure_rate}")
        
        # Get image URL using the enum as key
        try:
            image_url = self.placeholder_urls[self.model]
        except KeyError:
            logger.error(f"No placeholder URL found for model: {self.model}")
            logger.debug(f"Available keys in placeholder_urls: {list(self.placeholder_urls.keys())}")
            # Fallback to a default URL
            image_url = "https://via.placeholder.com/512x512?text=Generated+Image"
        logger.debug(f"Selected placeholder URL: {image_url}")
        
        success_result = {
            "success": True,
            "imageUrl": image_url
        }
        logger.info(f"Returning success result: {success_result}")
        return success_result

logger.info("AI Simulator module loaded successfully")