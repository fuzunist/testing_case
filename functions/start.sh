#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set environment variables
export FUNCTIONS_FRAMEWORK_TARGET=main
export GOOGLE_APPLICATION_CREDENTIALS=""
export FIREBASE_CONFIG='{"projectId":"demo-case-study"}'

# Start multiple functions
echo "Starting Firebase Functions with Functions Framework..."

# Start createGenerationRequest function
functions-framework --target=createGenerationRequest --signature-type=firebase --port=5001 &

# Wait for services to start
echo "Functions are starting..."
sleep 5

# Keep the script running
wait 