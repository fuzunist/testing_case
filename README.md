# AI Image Generation Backend - Case Study

This repository contains the solution for the **AI Image Generation Backend System** case study. The system is built entirely with Python on the Firebase platform (Cloud Functions and Firestore) and is designed for scalability, robustness, and maintainability.

It includes a credit-based economy, RESTful APIs for core operations, AI model simulation with failure handling, and a sophisticated weekly reporting mechanism with anomaly detection.

## Key Features

-   **Credit-Based Economy**: Manages user credits with atomic deductions for image generation and automated refunds for failures.
-   **Scalable APIs**: Provides endpoints to create generation requests and query user credit balances and history.
-   **AI Model Simulation**: Simulates two different AI models (`model-a`, `model-b`) with a configurable failure rate to test system resilience.
-   **Advanced Scheduled Reporting**: A weekly scheduled function aggregates usage data, calculates success/failure metrics, and performs **anomaly detection** to identify unusual usage patterns.
-   **Comprehensive Testing**: Includes a suite of automated `pytest` tests covering all key business logic, including credit management, input validation, and report generation.
-   **Emulator-Ready**: Comes with a pre-configured initial dataset for seamless setup and testing in the Firebase Local Emulator environment.

---

## Architecture and Design Decisions

This section outlines the key architectural choices made during the development of the system.

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
-   [Python 3.10+](https://www.python.org/downloads/)
-   A Java Development Kit (JDK) is required by the Firebase Emulators.

### Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://your-repository-link.git
    cd your-repository-directory
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

2.  **Manual Start (Alternative):**
    If you prefer to start services manually:

    ```bash
    # Terminal 1: Start Python Functions
    cd functions
    source venv/bin/activate
    pip install -r requirements.txt
    python -m functions_framework --target=main --port=5001
    
    # Terminal 2: Start Firebase Emulators
    firebase emulators:start --import=./initial_data --project=demo-case-study
    ```

3.  **Emulator UI:**
    Once running, you can access the powerful Emulator UI at [http://localhost:4000](http://localhost:4000). Here you can:
    -   View the Firestore database and see records being created in real-time.
    -   Monitor logs from the Cloud Functions.
    -   Trigger functions manually.

---

## API Endpoints & Usage

Here are some `cURL` examples for interacting with the deployed APIs.

*(Note: The port for the functions emulator may vary. Check the output of the `firebase emulators:start` command.)*

### 1. Create Generation Request

```bash
curl -X POST http://127.0.0.1:5001/demo-case-study/us-central1/createGenerationRequest \
-H "Content-Type: application/json" \
-d '{
    "userId": "test-user-1",
    "model": "model-a",
    "style": "anime",
    "color": "vibrant",
    "size": "512x512",
    "prompt": "A cat sitting on a futuristic throne"
}'
```

### 2. Get User Credits

```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/getUserCredits?userId=test-user-1"
```

### 3. Trigger Weekly Report Manually (for testing)

You can trigger the scheduled function manually via the Emulator UI or its direct endpoint:
```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/scheduleWeeklyReport"
```

---

## Running the Automated Tests

The project includes a comprehensive test suite using `pytest`. The tests run against the live emulators to ensure end-to-end integrity.

1.  **Ensure the emulators are running** (see steps above).

2.  **Run the tests:**
    Make sure your virtual environment is activated (`source functions/venv/bin/activate`) and run the following command from the project root:

    ```bash
    pytest
    ```

    The test suite covers:
    -   `test_input_validation.py`: Validation of all inputs for `createGenerationRequest`.
    -   `test_credit_deduction.py`: Correct credit deduction on successful generation.
    -   `test_refund_on_failure.py`: Correct credit refund when AI simulation fails.
    -   `test_insufficient_funds.py`: Rejection of requests from users with insufficient credits.
    -   `test_get_user_credits.py`: Correct retrieval of user balance and transaction history.
    -   `test_weekly_report.py`: Successful generation and data aggregation of the weekly report.