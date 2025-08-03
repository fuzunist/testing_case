# AI Image Generation Backend - Case Study

This repository contains the solution for the **AI Image Generation Backend System** case study. The system is built entirely with Python on the Firebase platform (Cloud Functions and Firestore) and is designed for scalability, robustness, and maintainability.

It includes a credit-based economy, RESTful APIs for core operations, AI model simulation with failure handling, and a sophisticated weekly reporting mechanism with anomaly detection.

## Important Notes

### ⚠️ Model Naming Convention
**IMPORTANT**: The case study mentions "Model A" and "Model B", but the system expects lowercase kebab-case format:
- Use `"model-a"` instead of `"Model A"`
- Use `"model-b"` instead of `"Model B"`

### Initial Data Configuration
The system requires the following collections to be populated in Firestore:
- **styles**: realistic, anime, oil painting, sketch, cyberpunk, watercolor
- **colors**: vibrant, monochrome, pastel, neon, vintage  
- **sizes**: 512x512 (1 credit), 1024x1024 (3 credits), 1024x1792 (4 credits)

The initial data export includes test users (`testUser1` with 100 credits and `testUser2` with 10 credits).

## Key Features

-   **Credit-Based Economy**: Manages user credits with atomic deductions for image generation and automated refunds for failures.
-   **Scalable APIs**: Provides endpoints to create generation requests and query user credit balances and history.
-   **AI Model Simulation**: Simulates two different AI models (`model-a`, `model-b`) with a configurable failure rate (~5%) to test system resilience.
-   **Advanced Scheduled Reporting**: A weekly scheduled function aggregates usage data, calculates success/failure metrics, and performs **anomaly detection** to identify unusual usage patterns.
-   **Comprehensive Testing**: Includes a suite of automated `pytest` tests covering all key business logic, including credit management, input validation, and report generation.
-   **Emulator-Ready**: Comes with a pre-configured initial dataset for seamless setup and testing in the Firebase Local Emulator environment.
-   **Mock Credentials Support**: The system automatically uses mock credentials in the emulator environment, eliminating authentication issues during local development.

## Recent Updates & Fixes

### 🔧 Latest Improvements (Aug 4, 2025)
1.  **Architectural Simplification**: Refactored the file structure for clarity and adherence to common standards. The core business logic now resides in `handlers.py`, the entry point for the Functions Framework is `main.py`, and redundant files have been removed. This results in a more intuitive and maintainable codebase.
2.  **Flexible Configuration**: Refactored configuration handling (`config.py`) to use environment variables for key parameters like the AI model's failure rate. This moves configuration out of the code, allowing for easier changes in different environments (dev, prod) without requiring a new deployment.
3.  **Consistent API Responses**: Fixed a critical bug where manually triggering the `scheduleWeeklyReport` endpoint returned an empty response.
4.  **Enhanced Error Handling & Bug Fixes**:
    -   Resolved a `TypeError` in the anomaly detection logic by correcting the class structure in `config.py`.
    -   Added proper HTTP status code mapping for Firebase errors.
5.  **Improved Logging**: Added detailed logging for critical code paths.
6.  **✅ Fully Automated Testing**:
    -   Introduced a `./run-tests.sh` script to fully automate the testing process (emulator startup, test execution, and cleanup).
    -   The entire test suite is fully operational and passing.
7.  **Fully Automated Setup**:
    -   The initial data setup is now fully automated via the `--import` flag. The `./start-emulator.sh` script now sets up a ready-to-use environment with a single command.

---

## Architecture and Design Decisions

This section outlines the key architectural choices made during the development of the system.

### Key Technical Updates

-   **Mock Credentials for Emulator**: The system automatically uses mock credentials when running in the Firebase Emulator environment, eliminating the need for actual Google Cloud credentials during local development.
-   **Python 3 Compatibility**: All commands use `python3` explicitly to ensure compatibility across different systems.

### 1. Database Schema (Firestore)

The Firestore database is structured to be both scalable and easy to query.

-   **`users`**: Stores user-specific data, including their current `credits`.
    -   `/users/{userId}`
-   **`transactions` (Subcollection)**: Each user has a dedicated `transactions` subcollection. This is a key design decision for scalability. Instead of a single root-level collection, this approach ensures that queries for a user's transaction history remain fast and efficient, regardless of the total number of transactions in the system.
    -   `/users/{userId}/transactions/{transactionId}`
-   **`generationRequests`**: A root-level collection to store details of every image generation request, including status (`pending`, `completed`, `failed`), cost, and all user-selected parameters.
-   **`reports`**: Stores the output of the `scheduleWeeklyReport` function. Each document represents a weekly summary with aggregated metrics and detected anomalies.
-   **Configuration Collections (`styles`, `colors`, `sizes`)**: These collections store the valid options for generation requests and their associated costs. They are automatically imported when the emulator starts. This makes the system extensible—new options can be added directly to the database without any code changes by exporting the data again.

### 2. Core Logic & File Structure (Firebase Functions)

All business logic is encapsulated within Firebase Functions written in Python, following a clean and maintainable structure:

-   **`main.py` (Entry Point)**: This is the main entry point for the Google Functions Framework. It receives all incoming HTTP requests and routes them to the appropriate handler function. It adapts the Flask-based request into a format that the Firebase Functions can understand.
-   **`handlers.py` (Business Logic)**: This file contains the core application logic for each of the main API endpoints:
    -   `createGenerationRequest`: Handles request validation, atomic credit deduction (using Firestore Transactions), triggers the AI simulation, and manages the refund process on failure.
    -   `getUserCredits`: Retrieves user credit balances and their transaction history.
    -   `scheduleWeeklyReport`: Contains the logic for aggregating weekly data, performing anomaly detection, and saving the final report.
-   **`config.py`**: Centralizes all application configuration, such as AI model details, anomaly detection thresholds, and image generation options. It is designed to be flexible, pulling sensitive or environment-specific values from environment variables.
-   **`ai_simulator.py`**: A simple module that simulates the behavior of the AI models, including a configurable failure rate to test the system's resilience and refund logic.

-   **`createGenerationRequest` (HTTPS Function)**:
    -   **Atomicity**: Uses a Firestore Transaction (`@firestore.transactional`) to perform the credit deduction and creation of the generation request record as a single, atomic operation. This guarantees that a user's credits are never deducted without a corresponding request record being created.
    -   **Failure & Refund**: If the AI model simulation fails, a refund is automatically triggered. The refund logic is separated into its own transactional function (`_refund_credits`) to ensure robustness. The request's status is updated to `failed`.
-   **`getUserCredits` (HTTPS Function)**:
    -   Retrieves the user's current balance and queries their `transactions` subcollection to provide a clean, user-specific history.
-   **`scheduleWeeklyReport` (Scheduled Function)**:
    -   **Time-Scoped Aggregation**: Runs every Monday and processes requests from the last 7 days only, ensuring reports are consistent and not duplicative.
    -   **Anomaly Detection**: This is a critical feature. The function compares the current week's metrics against the *previous week's report* to detect anomalies like:
        -   A significant drop in the overall success rate.
        -   An unusual spike in total requests or credit consumption (e.g., >3x the previous week).
        -   A sudden increase in the failure rate for a specific model, style, or size.
    -   The findings are stored in an `anomalies` array within the report document, making it easy to monitor system health.

### 3. Architectural Refinements

-   **Single Point of Routing**: Originally, the system had a multi-layered routing mechanism split between `functions_wrapper.py` and `main.py`. This has been refactored to a single, clear routing implementation in `functions_wrapper.py`. This change simplifies the request lifecycle, reduces code duplication, and makes the system easier to debug and maintain.
-   **Consistent Response Handling**: A bug was identified where manually triggering the scheduled `scheduleWeeklyReport` function resulted in an empty HTTP response. This was due to an incompatibility between the response object generated by a scheduled function and the response handling logic in the wrapper. The fix involved manually constructing a standard Flask response, ensuring that all API endpoints, regardless of their trigger type, provide consistent and reliable JSON outputs.
-   **Environment-Driven Configuration**: Key operational parameters, such as the AI model's failure rate, have been externalized from the code and are now configurable via environment variables (e.g., `AI_DEFAULT_FAILURE_RATE`). This follows the best practice of separating configuration from code, which is critical for managing different deployment environments (development, staging, production) and improves the system's overall flexibility.

---

## Getting Started

### Prerequisites

-   [Firebase CLI](https://firebase.google.com/docs/cli#install)
-   [Python 3.10+](https://www.python.org/downloads/) - Make sure `python3` command is available
-   A Java Development Kit (JDK) is required by the Firebase Emulators.

### Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/fuzunist/testing_case.git
    cd testing_case
    ```

2.  **Set up the Python Virtual Environment:**
    The project is pre-configured to use a virtual environment located in `functions/venv`.
    ```bash
    # Create and activate the virtual environment
    python3 -m venv functions/venv
    source functions/venv/bin/activate

    # Install dependencies
    pip install -r functions/requirements.txt
    ```

### Running the System with Firebase Emulators

The entire system is designed to be run locally using the Firebase Emulator Suite with Python Functions support.

1.  **Quick Start (Recommended):**
    Simply run the automated startup script from the project root:

    ```bash
    ./start-emulator.sh
    ```

    This script will:
    - Clean up any existing processes
    - Set up the Python virtual environment
    - Install all dependencies
    - Start Python Functions Framework
    - Start Firebase Emulators with all initial data (users and configurations) automatically imported.
    - Verify all services are running
    - Display test commands

2.  **Manual Start (Alternative):**
    If you prefer to start services manually:

    ```bash
    # Terminal 1: Start Python Functions
    cd functions
    source venv/bin/activate
    pip install -r requirements.txt
    FIRESTORE_EMULATOR_HOST="127.0.0.1:8080" \
    GCLOUD_PROJECT="demo-case-study" \
    GOOGLE_CLOUD_PROJECT="demo-case-study" \
    FIREBASE_AUTH_EMULATOR_HOST="127.0.0.1:9099" \
    python3 -m functions_framework --target=main --source=main.py --port=5001
    
    # Terminal 2: Start Firebase Emulators
    firebase emulators:start --only auth,firestore,database --import=./initial_data --project=demo-case-study
    ```
    
    **Note:** The system uses mock credentials for the emulator environment, so no actual Google Cloud credentials are needed.

3.  **Emulator UI:**
    Once running, you can access the powerful Emulator UI at [http://localhost:4000](http://localhost:4000). Here you can:
    -   View the Firestore database and see records being created in real-time.
    -   Monitor logs from the Cloud Functions.
    -   Trigger functions manually.

---

## API Endpoints & Usage

Here are some `cURL` examples for interacting with the deployed APIs.

*(Note: The initial data includes two test users: `testUser1` (100 credits) and `testUser2` (10 credits))*

**⚠️ Prerequisites**: Make sure you have run the configuration setup script first (see "Initial Data Configuration" section).

### 1. Create Generation Request

⚠️ **Note**: Use `"model-a"` or `"model-b"` (lowercase with hyphen), not "Model A" or "Model B".

```bash
curl -X POST http://127.0.0.1:5001/demo-case-study/us-central1/createGenerationRequest \
-H "Content-Type: application/json" \
-d '{
    "userId": "testUser1",
    "model": "model-a",
    "style": "anime",
    "color": "vibrant",
    "size": "512x512",
    "prompt": "A cat sitting on a futuristic throne"
}'
```

**Expected Response:**
```json
{
    "generationRequestId": "abc123",
    "deductedCredits": 1,
    "imageUrl": "https://storage.googleapis.com/.../placeholder-image.png"
}
```

**Possible Error Responses:**
- `400 Bad Request`: "Insufficient credits." - When user doesn't have enough credits
- `400 Bad Request`: "Invalid model 'Model A'. Please use one of ['model-a', 'model-b']" - Wrong model format
- `500 Internal Server Error`: "AI generation failed, credits refunded." - When AI simulation fails (credits are automatically refunded)
- `200 OK`: A full JSON response containing the generated weekly report.

### 2. Get User Credits

```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/getUserCredits?userId=testUser1"
```

### 3. Trigger Weekly Report Manually (for testing)

You can trigger the scheduled function manually via the Emulator UI or its direct endpoint:
```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/scheduleWeeklyReport"
```
**Expected Response:**
```json
{
    "totalRequests": 5,
    "totalCreditsSpent": 10,
    "totalCreditsRefunded": 0,
    "successRate": 100.0,
    "byModel": { ... },
    "byStyle": { ... },
    "bySize": { ... },
    "anomalies": [ ... ],
    "generatedAt": "..."
}
```

---

## Running the Automated Tests

The most reliable way to verify all system functionalities is by using the automated test script.

### One-Command Testing (Recommended)

A dedicated script, `run-tests.sh`, has been created to automate the entire testing process. This is the recommended way to run the tests as it handles the complete lifecycle: starting emulators, running tests, and cleaning up afterward.

**To run the full test suite:**

```bash
./run-tests.sh
```

This script will:
1.  **Start** all necessary Firebase emulators and Python functions in the background.
2.  **Wait** for the services to initialize.
3.  **Execute** the entire `pytest` suite against the live emulators.
4.  **Report** a clear "✅ SUCCESS" or "❌ FAILURE" message.
5.  **Automatically shut down** and clean up all background processes.

### Manual Test Execution (Alternative)

If you prefer to run the tests manually while the services are already running (e.g., via `./start-emulator.sh`), you can use the following command:

```bash
# Ensure the virtual environment is active if you opened a new terminal
source functions/venv/bin/activate
    
# Run the full test suite
FIRESTORE_EMULATOR_HOST="127.0.0.1:8080" pytest
```

The test suite covers:
-   Input validation for `createGenerationRequest`
-   Credit deduction and management
-   AI simulation failure and refund logic
-   User balance and transaction history retrieval
-   Weekly report generation and anomaly detection

---

## Testing Status

### ✅ Fully Tested and Validated

Following extensive testing and debugging, the system is now **fully validated** and all automated tests are passing.

- **User Credit Management**: Correct deduction, transaction logging, and insufficient funds handling.
- **AI Model Simulation**: Both success and failure scenarios work as expected.
- **Automatic Refunds**: Credits are correctly refunded to the user upon AI generation failure, with all database records updated atomically.
- **Input Validation**: All API parameters (`model`, `style`, `color`, `size`) are validated.
- **Weekly Reporting**: The scheduled function correctly aggregates data, calculates metrics, and performs anomaly detection. The manual trigger now returns a full JSON report.
- **Full Test Coverage**: All 9 automated `pytest` tests are **passing**.

### ✅ Ready for Evaluation

All previously identified limitations have been resolved. The system has been thoroughly tested, validated, and is robust and ready for evaluation.

---

## Troubleshooting

### Common Issues

1.  **"Invalid style/color/size" Errors**
    - **SOLUTION**: This error should no longer occur, as all configuration data is now automatically imported when the emulator starts using `./start-emulator.sh`. If you are running the system manually, ensure you use `firebase emulators:start --import=./initial_data`.

2.  **"Invalid model 'Model A'" Error**
    - **SOLUTION**: Use lowercase kebab-case format: `"model-a"` or `"model-b"`. The system expects this format, not "Model A".

3. **"Your default credentials were not found" Error**
   - **SOLUTION**: This should not happen when using the provided scripts, as they configure the emulator environment. If running manually, ensure `FIRESTORE_EMULATOR_HOST` is set to `127.0.0.1:8080`.

4. **Connection Refused Errors**
   - **SOLUTION**: Ensure Firebase emulators are running (`./start-emulator.sh`) before making API calls or running tests.
