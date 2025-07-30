import pytest
from firebase_functions.testing import TestClient
import functions.main
import os
import firebase_admin
from firebase_admin import credentials, firestore

# --- Emulator Setup ---
# Point the SDK to the local Firestore emulator.
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

@pytest.fixture(scope="session")
def app_client():
    """
    Provides a test client for the Flask app that points to the emulator.
    This fixture has a 'session' scope, so it's initialized only once.
    """
    if not firebase_admin._apps:
        # Use mock credentials for the emulator.
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {"projectId": "demo-case-study"})
    
    return TestClient(functions.main.app)


@pytest.fixture(autouse=True)
def clean_firestore(app_client):
    """
    A fixture that automatically cleans up the Firestore emulator database
    after every test, ensuring test isolation.
    """
    # This part runs before each test
    yield
    # This part runs after each test
    db = firestore.client()
    collections = ["users", "generationRequests", "reports"]
    for collection_name in collections:
        coll_ref = db.collection(collection_name)
        docs = coll_ref.stream()
        for doc in docs:
            # If there are subcollections, they need to be cleaned too.
            if collection_name == "users":
                sub_coll_ref = doc.reference.collection("transactions")
                sub_docs = sub_coll_ref.stream()
                for sub_doc in sub_docs:
                    sub_doc.reference.delete()
            doc.reference.delete()