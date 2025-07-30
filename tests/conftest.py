import os
import pytest
import requests
import time
import json
from google.cloud import firestore
import subprocess

# Set environment variables for emulator
os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'
os.environ['FUNCTIONS_EMULATOR_HOST'] = 'localhost:5001'

@pytest.fixture(scope="session", autouse=True)
def firebase_emulator():
    """Start Firebase emulators for testing session"""
    print("Starting Firebase emulators...")
    
    # Start emulators with initial data
    process = subprocess.Popen(
        ['firebase', 'emulators:start', '--import=./initial_data', '--project=demo-project'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='/workspace'
    )
    
    # Wait for emulators to start
    time.sleep(10)
    
    # Verify emulators are running
    try:
        response = requests.get('http://localhost:4000')
        if response.status_code != 200:
            raise Exception("Emulator UI not accessible")
    except Exception as e:
        print(f"Error starting emulators: {e}")
        process.terminate()
        raise
    
    yield process
    
    # Cleanup
    process.terminate()
    process.wait()


@pytest.fixture
def firestore_client():
    """Firestore client for direct database operations"""
    return firestore.Client(project='demo-project')


@pytest.fixture
def api_base_url():
    """Base URL for Firebase Functions"""
    return "http://localhost:5001/demo-project/us-central1"


@pytest.fixture(autouse=True)
def reset_test_users(firestore_client):
    """Reset test users to initial state before each test"""
    # Reset testUser1 to 100 credits
    firestore_client.collection('users').document('testUser1').set({'credits': 100})
    
    # Reset testUser2 to 10 credits
    firestore_client.collection('users').document('testUser2').set({'credits': 10})
    
    # Clear transaction histories
    for user_id in ['testUser1', 'testUser2']:
        transactions = firestore_client.collection('users').document(user_id).collection('transactions').stream()
        for transaction in transactions:
            transaction.reference.delete()
    
    # Clear generation requests
    requests = firestore_client.collection('generationRequests').stream()
    for request in requests:
        request.reference.delete()
    
    yield