#!/bin/bash

echo "🚀 Starting AI Image Generation Backend..."
echo "=========================================="

# Function to check if a port is in use
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

# Comprehensive cleanup function
cleanup_emulators() {
    echo "🧹 Performing comprehensive cleanup..."
    
    # Kill Firebase emulator processes
    echo "  → Stopping Firebase emulator processes..."
    pkill -f "firebase-tools" 2>/dev/null || true
    pkill -f "firebase emulators" 2>/dev/null || true
    pkill -f "java.*firebase" 2>/dev/null || true
    pkill -f "node.*firebase" 2>/dev/null || true
    
    # Kill Python functions
    echo "  → Stopping Python functions..."
    pkill -f "python.*functions_framework" 2>/dev/null || true
    pkill -f "python.*main.py" 2>/dev/null || true
    
    # Kill Java processes (Firestore emulator uses Java)
    echo "  → Stopping Java processes..."
    pkill -f java 2>/dev/null || true
    
    # Additional Firebase-specific process cleanup
    pkill -f "emulator-suite" 2>/dev/null || true
    pkill -f "cloud-firestore-emulator" 2>/dev/null || true
    pkill -f "firebase-database-emulator" 2>/dev/null || true
    
    # Clean up Firebase emulator hub
    pkill -f "hub.js" 2>/dev/null || true
    
    # Wait for processes to terminate
    sleep 3
    
    # Clean up emulator temporary files
    echo "  → Cleaning temporary files..."
    # rm -rf ~/.cache/firebase/emulators/ 2>/dev/null || true  # Commented out to keep JAR cache
    rm -f firebase-debug.log 2>/dev/null || true
    rm -f firestore-debug.log 2>/dev/null || true
    rm -f database-debug.log 2>/dev/null || true
    rm -f ui-debug.log 2>/dev/null || true
    rm -f pubsub-debug.log 2>/dev/null || true
    
    # Clean up any PID files
    rm -f *.pid 2>/dev/null || true
    
    # Force kill any remaining processes on emulator ports
    echo "  → Force cleaning ports..."
    for port in 4000 4400 4500 5001 8080 8085 9000 9099 9150 9199; do
        if check_port $port; then
            echo "    - Killing process on port $port"
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    # Final wait to ensure everything is cleaned up
    sleep 2
    
    echo "  ✅ Cleanup complete!"
    echo ""
}

# Run comprehensive cleanup
cleanup_emulators

# Check if ports are free after cleanup
for port in 4000 5001 8080 9000 9099; do
    if check_port $port; then
        echo "⚠️  Port $port is in use. Attempting to free it..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
done

# Set environment variables for emulator first
echo "🔧 Setting up emulator environment..."
export FIRESTORE_EMULATOR_HOST="0.0.0.0:8080"
export GCLOUD_PROJECT="demo-case-study"
export GOOGLE_CLOUD_PROJECT="demo-case-study"
export FIREBASE_AUTH_EMULATOR_HOST="0.0.0.0:9099"

# Start Python Functions in background
echo "🐍 Starting Python Functions..."
cd functions
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Start functions with environment variables
FIRESTORE_EMULATOR_HOST="0.0.0.0:8080" \
GCLOUD_PROJECT="demo-case-study" \
GOOGLE_CLOUD_PROJECT="demo-case-study" \
FIREBASE_AUTH_EMULATOR_HOST="0.0.0.0:9099" \
python -m functions_framework --target=main --source=main.py --port=5001 --debug &
FUNCTIONS_PID=$!
cd ..

# Wait for functions to start
echo "⏳ Waiting for Functions to start..."
sleep 5

# Start Firebase Emulators
echo "🔥 Starting Firebase Emulators..."
firebase emulators:start --only auth,firestore --import=./initial_data --project=demo-case-study --debug &
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

if curl -s http://127.0.0.1:5001 >/dev/null; then
    echo "✅ Functions: http://127.0.0.1:5001"
else
    echo "❌ Functions are not responding"
fi

echo ""
echo "📝 Test Commands:"
echo "=========================================="
echo "1. Get user credits:"
echo "   curl -X GET 'http://127.0.0.1:5001/demo-case-study/us-central1/getUserCredits?userId=test-user-1'"
echo ""
echo "2. Create generation request:"
echo "   curl -X POST http://127.0.0.1:5001/demo-case-study/us-central1/createGenerationRequest \\"
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
echo "3. Trigger weekly report:"
echo "   curl -X GET 'http://127.0.0.1:5001/demo-case-study/us-central1/scheduleWeeklyReport'"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo "=========================================="

# Keep script running and handle cleanup
trap "echo '🛑 Stopping services...'; kill $FUNCTIONS_PID $EMULATOR_PID 2>/dev/null; exit" INT TERM
wait 