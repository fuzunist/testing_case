import pytest
import logging
from firebase_admin import firestore
import firebase_admin

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=== Initializing test configuration ===")

# This is a one-time setup for all tests.
if not firebase_admin._apps:
    logger.info("Initializing Firebase Admin SDK for tests with default credentials")
    # We initialize with default credentials, which will be the emulator credentials
    # when the FIRESTORE_EMULATOR_HOST environment variable is set by the pytest-firebase plugin.
    firebase_admin.initialize_app()
    logger.info("Firebase Admin SDK initialized for tests")
else:
    logger.info("Firebase Admin SDK already initialized")


@pytest.fixture(scope="session")
def db():
    """
    Provides a session-scoped Firestore client connected to the emulator.
    This ensures we don't have to initialize the client in every test.
    """
    logger.info("Creating session-scoped Firestore client")
    client = firestore.client()
    logger.info("Firestore client created successfully")
    return client


@pytest.fixture
def managed_user(db):
    """
    A fixture that creates a user for a test and cleans it up afterward.

    This is a "factory as a fixture" pattern. It returns a function that
    the test can call to create a user with specific properties.

    The teardown logic handles deleting the user, their transactions,
    and any generation requests they created.
    """
    logger.info("=== Setting up managed_user fixture ===")
    created_user_ids = []
    created_generation_request_ids = []

    def _create_user(user_id: str, credits: int = 100):
        """The actual factory function that creates a user."""
        logger.info(f"Creating user with ID: {user_id}, Credits: {credits}")
        user_ref = db.collection("users").document(user_id)
        user_ref.set({"credits": credits})
        created_user_ids.append(user_id)
        logger.info(f"User '{user_id}' created successfully")
        return user_id

    # The test runs here
    logger.info("Yielding managed_user factory function")
    yield _create_user

    # --- Teardown ---
    # This code runs after the test has finished.
    logger.info("=== Starting managed_user fixture teardown ===")
    logger.info(f"Cleaning up {len(created_user_ids)} managed user(s)...")
    
    for user_id in created_user_ids:
        logger.info(f"Cleaning up user: {user_id}")
        
        # Find all generation requests by this user to clean up the root collection
        logger.debug(f"Finding generation requests for user: {user_id}")
        requests_query = db.collection("generationRequests").where("userId", "==", user_id).stream()
        request_count = 0
        for req in requests_query:
            req.reference.delete()
            request_count += 1
            logger.debug(f"  - Deleted generationRequest: {req.id}")
        
        if request_count > 0:
            logger.info(f"  - Deleted {request_count} generation requests for user '{user_id}'")

        # Find and delete all transactions in the subcollection
        logger.debug(f"Finding transactions for user: {user_id}")
        trans_query = db.collection("users").document(user_id).collection("transactions").stream()
        transaction_count = 0
        for tran in trans_query:
            tran.reference.delete()
            transaction_count += 1
        
        if transaction_count > 0:
            logger.info(f"  - Deleted {transaction_count} transactions for user '{user_id}'")
        
        # Finally, delete the user document itself
        db.collection("users").document(user_id).delete()
        logger.info(f"  - Deleted user: {user_id} and their transactions.")
    
    logger.info("Managed_user fixture teardown completed")

@pytest.fixture(scope="session")
def app_client():
    """
    Provides a test client for making requests to the Firebase Functions emulator.
    This fixture is provided by the `pytest-firebase` plugin. We just give it a
    more convenient name here. This assumes the plugin is installed and configured.
    """
    logger.info("=== Setting up app_client fixture ===")
    
    # This is a placeholder. The actual implementation depends on how you've set up
    # your test client. If using Flask, for example, you'd yield app.test_client().
    # For this project, we assume a global client is configured or passed in.
    # We'll rely on the existing setup that seems to work via `app_client` name.
    
    # A simple mock client for demonstration if no real one is configured.
    from flask import Flask
    
    # We need to import the functions to register them with Flask
    logger.info("Importing Firebase Functions for Flask app")
    from functions.main import createGenerationRequest, getUserCredits

    logger.info("Creating Flask test app")
    app = Flask(__name__)
    app.add_url_rule("/createGenerationRequest", view_func=createGenerationRequest, methods=["POST"])
    app.add_url_rule("/getUserCredits", view_func=getUserCredits, methods=["GET"])
    
    logger.info("Flask test app created successfully")
    logger.info("Available routes:")
    logger.info("  - POST /createGenerationRequest")
    logger.info("  - GET /getUserCredits")

    return app.test_client()

logger.info("Test configuration initialization completed")