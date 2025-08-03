#!/bin/bash
# This script automates the testing process by running the test suite.
# It assumes that the necessary emulators are already running.

echo "🚀 Running the Test Suite for AI Image Generation Backend..."
echo "======================================================================"

# Ensure we are in the project root directory
cd "$(dirname "$0")"

# Activate virtual environment and run the tests.
echo ""
echo "🐍 Activating virtual environment and running pytest..."
echo "--------------------------------------------------"
source functions/venv/bin/activate

# Set the emulator host for pytest and execute the test suite
FIRESTORE_EMULATOR_HOST="127.0.0.1:8080" pytest

# Capture the exit code of the pytest command. 0 means success.
PYTEST_EXIT_CODE=$?
echo "--------------------------------------------------"


# Report the final result.
echo ""
echo "======================= TEST RESULT ======================="
if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  echo "✅ SUCCESS: All tests passed!"
else
  echo "❌ FAILURE: Some tests failed. Please review the output above."
fi
echo "==========================================================="

# Exit with the same exit code as pytest, which is useful for CI/CD environments.
exit $PYTEST_EXIT_CODE 