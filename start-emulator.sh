#!/bin/bash

echo "🚀 Starting AI Image Generation Backend..."
echo "=========================================="

# Function to check if a port is in use
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f firebase 2>/dev/null || true
pkill -f "python.*functions_framework" 2>/dev/null || true
pkill -f java 2>/dev/null || true
sleep 2

# Check if ports are free
for port in 4000 5001 8080 9000 9099; do
    if check_port $port; then
        echo "⚠️  Port $port is in use. Attempting to free it..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
done

# Start Python Functions in background
echo "🐍 Starting Python Functions..."
cd functions
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
FUNCTIONS_FRAMEWORK_TARGET=main python -m functions_framework --target=main --port=5001 --debug &
FUNCTIONS_PID=$!
cd ..

# Wait for functions to start
echo "⏳ Waiting for Functions to start..."
sleep 5

# Start Firebase Emulators
echo "🔥 Starting Firebase Emulators..."
firebase emulators:start --import=./initial_data --project=demo-case-study &
EMULATOR_PID=$!

# Wait for emulators to fully start
echo "⏳ Waiting for Emulators to start..."
sleep 10

# Check if services are running
echo ""
echo "🔍 Checking services status..."
echo "=========================================="

if curl -s http://localhost:4000 >/dev/null; then
    echo "✅ Emulator UI: http://localhost:4000"
else
    echo "❌ Emulator UI is not responding"
fi

if curl -s http://localhost:5001 >/dev/null; then
    echo "✅ Functions: http://localhost:5001"
else
    echo "❌ Functions are not responding"
fi

echo ""
echo "📝 Test Commands:"
echo "=========================================="
echo "1. Get user credits:"
echo "   curl -X GET 'http://localhost:5001/getUserCredits?userId=test-user-1'"
echo ""
echo "2. Create generation request:"
echo "   curl -X POST http://localhost:5001/createGenerationRequest \\"
echo "   -H 'Content-Type: application/json' \\"
echo "   -d '{"
echo "       \"userId\": \"test-user-1\","
echo "       \"model\": \"model-a\","
echo "       \"style\": \"anime\","
echo "       \"color\": \"vibrant\","
echo "       \"size\": \"512x512\","
echo "       \"prompt\": \"A cat sitting on a futuristic throne\""
echo "   }'"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo "=========================================="

# Keep script running and handle cleanup
trap "echo '🛑 Stopping services...'; kill $FUNCTIONS_PID $EMULATOR_PID 2>/dev/null; exit" INT TERM
wait 