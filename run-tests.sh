#!/bin/bash
# This script automates the entire testing process.
# It starts the necessary emulators, runs the pytest suite, and then shuts everything down.

echo "🚀 Starting Automated Test Suite for AI Image Generation Backend..."
echo "======================================================================"

# Ensure we are in the project root directory
cd "$(dirname "$0")"

# 1. Start all services in the background using the existing startup script.
# We send it to the background and save its process ID.
./start-emulator.sh &
STARTUP_PID=$!

# 2. Set up a trap to ensure that background services are killed when this script exits,
# no matter if it's a success, failure, or user interruption.
trap "echo; echo '🛑 Shutting down all background services...'; kill $STARTUP_PID 2>/dev/null; exit" INT TERM EXIT

# 3. Wait for all services to initialize properly.
echo "⏳ Waiting 15 seconds for emulators and functions to be ready..."
sleep 15
echo "✅ Services are assumed to be ready."

# 4. Activate virtual environment and run the tests.
echo ""
echo "🐍 Activating virtual environment and running pytest..."
echo "--------------------------------------------------"
source functions/venv/bin/activate

# Set the emulator host for pytest and execute the test suite
FIRESTORE_EMULATOR_HOST="127.0.0.1:8080" pytest

# Capture the exit code of the pytest command. 0 means success.
PYTEST_EXIT_CODE=$?
echo "--------------------------------------------------"


# 5. Report the final result.
echo ""
echo "======================= TEST RESULT ======================="
if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  echo "✅ SUCCESS: All tests passed!"
else
  echo "❌ FAILURE: Some tests failed. Please review the output above."
fi
echo "==========================================================="

# The trap will automatically run on exit, cleaning up the background processes.
# Exit with the same exit code as pytest, which is useful for CI/CD environments.
exit $PYTEST_EXIT_CODE 