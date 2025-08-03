import logging
from enum import Enum
import os

# Configure logging for config module
logger = logging.getLogger(__name__)

logger.info("Loading configuration module...")

class ImageModels(Enum):
    """Enum for the available AI models."""
    model_a = "model-a"
    model_b = "model-b"

logger.info(f"ImageModels enum loaded with values: {[model.value for model in ImageModels]}")


class AnomalyThresholds:
    """Constants for detecting anomalies in weekly reports."""
    SUCCESS_RATE_DROP_RATIO = 0.5  # e.g., if success rate drops to 50% of last week's
    USAGE_SPIKE_MULTIPLIER = 3.0  # e.g., if usage is 3x higher than last week
    MIN_SAMPLES_FOR_ANOMALY = 10  # Minimum number of requests to trigger spike alerts
    SIGNIFICANT_FAILURE_RATE = 20.0  # A failure rate that is considered high on its own
    FAILURE_RATE_SPIKE_MULTIPLIER = 2.0  # e.g., if failure rate is 2x higher than last week

logger.info("AnomalyThresholds loaded with values:")
logger.info(f"  - SUCCESS_RATE_DROP_RATIO: {AnomalyThresholds.SUCCESS_RATE_DROP_RATIO}")
logger.info(f"  - USAGE_SPIKE_MULTIPLIER: {AnomalyThresholds.USAGE_SPIKE_MULTIPLIER}")
logger.info(f"  - MIN_SAMPLES_FOR_ANOMALY: {AnomalyThresholds.MIN_SAMPLES_FOR_ANOMALY}")
logger.info(f"  - SIGNIFICANT_FAILURE_RATE: {AnomalyThresholds.SIGNIFICANT_FAILURE_RATE}")
logger.info(f"  - FAILURE_RATE_SPIKE_MULTIPLIER: {AnomalyThresholds.FAILURE_RATE_SPIKE_MULTIPLIER}")


class AIModelsConfig:
    """
    Configuration for the AI model simulator.
    """
    # Default failure rate for the AI simulation.
    DEFAULT_FAILURE_RATE = float(os.getenv("AI_DEFAULT_FAILURE_RATE", 0.05))

    # Placeholder URLs for each simulated model.
    PLACEHOLDER_URLS = {
        ImageModels.model_a: "https://storage.googleapis.com/proudcity/mebanenc/uploads/2018/02/placeholder-image.png",
        ImageModels.model_b: "https://www.russorizio.com/wp-content/uploads/2016/07/ef3-placeholder-image.jpg"
    }

logger.info("AIModelsConfig loaded with values:")
logger.info(f"  - DEFAULT_FAILURE_RATE: {AIModelsConfig.DEFAULT_FAILURE_RATE}")
logger.info(f"  - PLACEHOLDER_URLS count: {len(AIModelsConfig.PLACEHOLDER_URLS)}")
for model, url in AIModelsConfig.PLACEHOLDER_URLS.items():
    logger.debug(f"    - {model.value}: {url}")

logger.info("Configuration module loaded successfully") 