import pytest
import logging
from firebase_admin import firestore, credentials
import firebase_admin
import os
from typing import Generator, Any
from flask import Flask, Request as FlaskRequest
from firebase_functions import https_fn

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=== Initializing test configuration ===")

# Set up emulator environment
os.environ['FIRESTORE_EMULATOR_HOST'] = '127.0.0.1:8080'
os.environ['FIREBASE_AUTH_EMULATOR_HOST'] = '127.0.0.1:9099'
os.environ['GCLOUD_PROJECT'] = 'demo-case-study'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'demo-case-study'

# Mock credential for emulator
class MockCredential(credentials.Base):
    def get_credential(self):
        from google.oauth2 import credentials as oauth2_credentials
        return oauth2_credentials.Credentials(token='mock-token')

# This is a one-time setup for all tests.
if not firebase_admin._apps:
    try:
        logger.info("Initializing Firebase Admin SDK for tests (emulator mode)")
        # Initialize for emulator with mock credentials
        firebase_admin.initialize_app(
            credential=MockCredential(),
            options={'projectId': 'demo-case-study'}
        )
        logger.info("Firebase Admin SDK initialized for tests")
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin SDK: {e}")
        raise


@pytest.fixture(scope="session")
def db() -> firestore.Client:
    """
    Provides a session-scoped Firestore client connected to the emulator.
    This ensures we don't have to initialize the client in every test.
    """
    logger.info("Creating session-scoped Firestore client")
    try:
        # Make sure emulator host is set
        assert os.getenv('FIRESTORE_EMULATOR_HOST') == '127.0.0.1:8080', "Firestore emulator not configured"
        
        client = firestore.client()
        logger.info("Firestore client created successfully")
        logger.info(f"Connected to Firestore emulator at {os.getenv('FIRESTORE_EMULATOR_HOST')}")
        
        # Test the connection
        test_ref = client.collection('_test_connection').document('test')
        test_ref.set({'test': True})
        test_ref.delete()
        logger.info("Firestore connection test successful")
        
        return client
    except Exception as e:
        logger.error(f"Failed to create Firestore client: {e}")
        pytest.fail(f"Could not connect to Firestore emulator: {e}")


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
        
        try:
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
        except Exception as e:
            logger.error(f"Error cleaning up user {user_id}: {e}")
    
    logger.info("Managed_user fixture teardown completed")


# Custom wrapper to convert Flask requests to Firebase Functions requests
class FirebaseFunctionWrapper:
    def __init__(self, firebase_function):
        self.firebase_function = firebase_function
        # Flask needs __name__ attribute for endpoint creation
        self.__name__ = firebase_function.__name__
    
    def __call__(self, *args, **kwargs):
        # Get Flask request
        from flask import request as flask_request
        
        # Create a mock Request that mimics firebase_functions.https_fn.Request
        class MockRequest:
            def __init__(self):
                self.method = flask_request.method
                self.path = flask_request.path
                self.headers = dict(flask_request.headers)
                self.args = flask_request.args.to_dict()
                # Handle JSON data
                try:
                    self.json = flask_request.get_json(force=True) if flask_request.data else None
                except:
                    self.json = None
                self.data = flask_request.data
            
            def get_json(self):
                return self.json
        
        # Create mock request
        firebase_request = MockRequest()
        
        # Call the Firebase function
        response = self.firebase_function(firebase_request)
        
        # Convert Firebase Functions Response to Flask response
        from flask import Response as FlaskResponse
        
        # Handle response based on its type
        if hasattr(response, 'body'):
            return FlaskResponse(
                response.body,
                status=response.status,
                headers=response.headers,
                mimetype=response.mimetype or 'text/plain'
            )
        else:
            # If it's a direct Response object, return it as is
            return response


@pytest.fixture(scope="session")
def app_client():
    """
    Provides a test client for making requests to the Firebase Functions.
    """
    logger.info("=== Setting up app_client fixture ===")
    
    # Import the functions
    logger.info("Importing Firebase Functions for Flask app")
    from functions.main import createGenerationRequest, getUserCredits
    
    logger.info("Creating Flask test app")
    app = Flask(__name__)
    
    # Wrap the Firebase functions
    wrapped_create = FirebaseFunctionWrapper(createGenerationRequest)
    wrapped_get_credits = FirebaseFunctionWrapper(getUserCredits)
    
    # Register routes
    app.add_url_rule("/createGenerationRequest", view_func=wrapped_create, methods=["POST"])
    app.add_url_rule("/getUserCredits", view_func=wrapped_get_credits, methods=["GET"])
    
    logger.info("Flask test app created successfully")
    logger.info("Available routes:")
    logger.info("  - POST /createGenerationRequest")
    logger.info("  - GET /getUserCredits")
    
    with app.test_client() as client:
        yield client

logger.info("Test configuration initialization completed")