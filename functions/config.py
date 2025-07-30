from enum import Enum


class ImageModels(Enum):
    """
    Enumeration for the available AI models.
    This is the single source of truth for model names.
    """
    model_a = "Model A"
    model_b = "Model B"


class AnomalyThresholds:
    """
    Constants for detecting anomalies in weekly reports.
    These values can be tuned to adjust sensitivity without changing logic.
    """
    # A factor to determine a significant drop in success rate.
    # e.g., 0.5 means a drop to less than 50% of the previous week's rate is an anomaly.
    SUCCESS_RATE_DROP_RATIO = 0.5

    # A multiplier to detect a spike in usage.
    # e.g., 3 means more than 3x the requests/credits of the previous week is an anomaly.
    USAGE_SPIKE_MULTIPLIER = 3.0

    # The minimum number of requests from a previous period required to perform
    # a reliable anomaly comparison.
    MIN_SAMPLES_FOR_ANOMALY = 10

    # A baseline failure rate percentage that is considered significant.
    # An anomaly is only flagged if the new failure rate is above this value.
    SIGNIFICANT_FAILURE_RATE = 20.0

    # A multiplier for detecting a spike in the failure rate of a specific category.
    # e.g., 2.0 means the failure rate has more than doubled.
    FAILURE_RATE_SPIKE_MULTIPLIER = 2.0


class AIModelsConfig:
    """
    Configuration for the AI model simulator.
    """
    # Default failure rate for the AI simulation.
    DEFAULT_FAILURE_RATE = 0.05

    # Placeholder URLs for each simulated model.
    PLACEHOLDER_URLS = {
        ImageModels.model_a: "https://storage.googleapis.com/proudcity/mebanenc/uploads/2018/02/placeholder-image.png",
        ImageModels.model_b: "https://www.russorizio.com/wp-content/uploads/2016/07/ef3-placeholder-image.jpg"
    } 