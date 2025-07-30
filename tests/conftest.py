import pytest
from firebase_admin import firestore
import firebase_admin

# This is a one-time setup for all tests.
if not firebase_admin._apps:
    # We initialize with default credentials, which will be the emulator credentials
    # when the FIRESTORE_EMULATOR_HOST environment variable is set by the pytest-firebase plugin.
    firebase_admin.initialize_app()


@pytest.fixture(scope="session")
def db():
    """
    Provides a session-scoped Firestore client connected to the emulator.
    This ensures we don't have to initialize the client in every test.
    """
    return firestore.client()


@pytest.fixture
def managed_user(db):
    """
    A fixture that creates a user for a test and cleans it up afterward.

    This is a "factory as a fixture" pattern. It returns a function that
    the test can call to create a user with specific properties.

    The teardown logic handles deleting the user, their transactions,
    and any generation requests they created.
    """
    created_user_ids = []
    created_generation_request_ids = []

    def _create_user(user_id: str, credits: int = 100):
        """The actual factory function that creates a user."""
        user_ref = db.collection("users").document(user_id)
        user_ref.set({"credits": credits})
        created_user_ids.append(user_id)
        return user_id

    # The test runs here
    yield _create_user

    # --- Teardown ---
    # This code runs after the test has finished.
    print(f"\nCleaning up {len(created_user_ids)} managed user(s)...")
    for user_id in created_user_ids:
        # Find all generation requests by this user to clean up the root collection
        requests_query = db.collection("generationRequests").where("userId", "==", user_id).stream()
        for req in requests_query:
            req.reference.delete()
            print(f"  - Deleted generationRequest: {req.id}")

        # Find and delete all transactions in the subcollection
        trans_query = db.collection("users").document(user_id).collection("transactions").stream()
        for tran in trans_query:
            tran.reference.delete()
        
        # Finally, delete the user document itself
        db.collection("users").document(user_id).delete()
        print(f"  - Deleted user: {user_id} and their transactions.")

@pytest.fixture(scope="session")
def app_client():
    """
    Provides a test client for making requests to the Firebase Functions emulator.
    This fixture is provided by the `pytest-firebase` plugin. We just give it a
    more convenient name here. This assumes the plugin is installed and configured.
    """
    # This is a placeholder. The actual implementation depends on how you've set up
    # your test client. If using Flask, for example, you'd yield app.test_client().
    # For this project, we assume a global client is configured or passed in.
    # We'll rely on the existing setup that seems to work via `app_client` name.
    
    # A simple mock client for demonstration if no real one is configured.
    from flask import Flask
    
    # We need to import the functions to register them with Flask
    from functions.main import createGenerationRequest, getUserCredits

    app = Flask(__name__)
    app.add_url_rule("/createGenerationRequest", view_func=createGenerationRequest, methods=["POST"])
    app.add_url_rule("/getUserCredits", view_func=getUserCredits, methods=["GET"])

    return app.test_client()