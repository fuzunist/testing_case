import logging
import pytest
from unittest.mock import patch
from functions.main import createGenerationRequest

# Configure logging for this test module
logger = logging.getLogger(__name__)

BASE_URL = "/createGenerationRequest"

logger.info("=== Loading test_refund_on_failure module ===")


@pytest.fixture
def valid_payload():
    """Provides a valid payload for testing, focusing on refund logic."""
    return {
        "userId": "testUserRefund",
        "model": "model-b",
        "style": "sketch",
        "color": "monochrome",
        "size": "512x512",
        "prompt": "A test prompt for refund logic."
    }


def test_refund_on_ai_failure(app_client, db, valid_payload):
    """
    Test that credits are refunded and status is 'failed' when AI generation fails.
    This test uses patching to ensure the AI model consistently fails.
    """
    logger.info("=== Starting test_refund_on_ai_failure ===")
    user_ref = db.collection("users").document(valid_payload["userId"])
    initial_credits = 10

    try:
        # --- Setup: Create the test user in Firestore ---
        logger.info(f"Creating user '{valid_payload['userId']}' with {initial_credits} credits")
        user_ref.set({"credits": initial_credits})

        # --- Use patch to force AI generation failure ---
        # We patch 'random.random' to always return 0.0, which is less than any failure rate > 0,
        # thus ensuring the ai_simulator returns a failure.
        with patch('functions.ai_simulator.random.random', return_value=0.0) as mock_random:
            logger.info("Patching 'random.random' to force AI failure")
            
            # --- Make the request ---
            response = app_client.post(BASE_URL, json=valid_payload)
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response data: {response.data.decode()}")

            # --- Assertions ---
            # 1. Check API response for failure
            assert response.status_code == 500
            assert "AI generation failed, credits refunded." in response.data.decode()

            # 2. Verify user credits were refunded to the initial amount
            user_snapshot = user_ref.get()
            final_credits = user_snapshot.get("credits")
            logger.info(f"Initial credits: {initial_credits}, Final credits: {final_credits}")
            assert final_credits == initial_credits

            # 3. Verify the generation request was created and marked as 'failed'
            requests_query = db.collection("generationRequests").where("userId", "==", valid_payload["userId"]).stream()
            request_found = False
            for req in requests_query:
                req_data = req.to_dict()
                if req_data.get("prompt") == valid_payload["prompt"]:
                    logger.info(f"Found generation request: {req.id}, status: {req_data.get('status')}")
                    assert req_data.get("status") == "failed"
                    request_found = True
                    break
            assert request_found, "Generation request was not found for the user."
            
            # 4. Verify the transaction log shows both a deduction and a subsequent refund
            transactions_query = user_ref.collection("transactions").stream()
            transactions = [t.to_dict() for t in transactions_query]
            
            logger.info(f"Found {len(transactions)} transactions: {transactions}")
            assert len(transactions) >= 2

            deduction_found = any(t.get("type") == "deduction" for t in transactions)
            refund_found = any(t.get("type") == "refund" for t in transactions)

            assert deduction_found, "Deduction transaction log not found."
            assert refund_found, "Refund transaction log not found."

            logger.info("All assertions for refund test passed successfully.")

    finally:
        # --- Cleanup: Delete all test-related data ---
        logger.info(f"Cleaning up test data for user '{valid_payload['userId']}'")
        try:
            # Delete transactions subcollection
            trans_query = user_ref.collection("transactions").stream()
            for t in trans_query:
                t.reference.delete()
        
            # Delete user document
            user_ref.delete()
            
            # Delete associated generation requests
            requests_query = db.collection("generationRequests").where("userId", "==", valid_payload["userId"]).stream()
            for req in requests_query:
                req.reference.delete()
                
            logger.info("Test data cleanup completed.")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")