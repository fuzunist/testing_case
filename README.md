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

**⚠️ IMPORTANT**: After starting the emulator, you need to populate the configuration collections. Run this command:

```bash
cd functions && source venv/bin/activate && cd ..
python3 << 'EOF'
import os
import firebase_admin
from firebase_admin import credentials, firestore

os.environ['FIRESTORE_EMULATOR_HOST'] = '127.0.0.1:8080'

class MockCredential(credentials.Base):
    def get_credential(self):
        from google.oauth2 import credentials as oauth2_credentials
        return oauth2_credentials.Credentials(token='mock-token')

if not firebase_admin._apps:
    firebase_admin.initialize_app(credential=MockCredential(), options={'projectId': 'demo-case-study'})

db = firestore.client()

# Setup configuration collections
styles = ['realistic', 'anime', 'oil painting', 'sketch', 'cyberpunk', 'watercolor']
for style in styles: db.collection('styles').document(style).set({'name': style})

colors = ['vibrant', 'monochrome', 'pastel', 'neon', 'vintage']
for color in colors: db.collection('colors').document(color).set({'name': color})

sizes = {'512x512': 1, '1024x1024': 3, '1024x1792': 4}
for size, credits in sizes.items(): db.collection('sizes').document(size).set({'credits': credits})

print("✅ Configuration collections created successfully!")
EOF
```

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

### 🔧 Latest Improvements (Aug 3, 2025)
1. **Enhanced Error Handling**: Added proper HTTP status code mapping for Firebase errors
2. **Improved Logging**: Added detailed logging for critical code paths.
3. **✅ Fixed and Validated Full `pytest` Suite**:
    - Repaired and enhanced the entire `pytest` suite to be fully operational with the emulator.
    - Corrected the refund simulation test (`test_refund_on_failure`) using mocking to reliably trigger failure scenarios.
    - Fixed the weekly report integration test (`test_weekly_report_integration`) by resolving scope and return type issues.
    - All 9 automated tests are now passing, ensuring the project is robust and fully validated against the case study requirements.
4. **Validated Features**:
    - All features from the case study are now covered by automated tests.

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
-   **Configuration Collections (`styles`, `colors`, `sizes`)**: These collections store the valid options for generation requests and their associated costs. This makes the system extensible—new options can be added directly to the database without any code changes.

### 2. Core Logic (Firebase Functions)

All business logic is encapsulated within Firebase Functions written in Python.

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
    - Start Firebase Emulators with initial data
    - Verify all services are running
    - Display test commands

    **⚠️ IMPORTANT**: After the emulator starts, run the configuration setup script (see "Initial Data Configuration" section above) to populate the required collections.

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
    python3 -m functions_framework --target=main --source=functions_wrapper.py --port=5001
    
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

### 2. Get User Credits

```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/getUserCredits?userId=testUser1"
```

### 3. Trigger Weekly Report Manually (for testing)

You can trigger the scheduled function manually via the Emulator UI or its direct endpoint:
```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/scheduleWeeklyReport"
```

---

## Running the Automated Tests

### Automated pytest Tests (Recommended)

The project includes a comprehensive and **fully functional** test suite using `pytest`. This is the recommended way to validate the entire system's functionality.

**To run the tests:**

1.  Make sure the emulators are running (`./start-emulator.sh`).
2.  Ensure the configuration data has been populated (see "Initial Data Configuration" section).
3.  Run the full test suite from the project root:

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
- **Weekly Reporting**: The scheduled function correctly aggregates data, calculates metrics, and performs anomaly detection.
- **Full Test Coverage**: All 9 automated `pytest` tests are **passing**.

### ✅ No Known Limitations

All previously identified limitations have been resolved. The system is robust and ready for evaluation.

---

## Troubleshooting

### Common Issues

1. **"Invalid style/color/size" Errors**
   - **SOLUTION**: Run the configuration setup script provided in the "Initial Data Configuration" section above. The collections must be populated after starting the emulator.

2. **"Invalid model 'Model A'" Error**
   - **SOLUTION**: Use lowercase kebab-case format: `"model-a"` or `"model-b"`. The system expects this format, not "Model A".

3. **"Your default credentials were not found" Error**
   - **SOLUTION**: This should not happen when using the provided scripts, as they configure the emulator environment. If running manually, ensure `FIRESTORE_EMULATOR_HOST` is set to `127.0.0.1:8080`.

4. **Connection Refused Errors**
   - **SOLUTION**: Ensure Firebase emulators are running (`./start-emulator.sh`) before making API calls or running tests.
