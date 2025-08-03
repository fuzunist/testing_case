# AI Image Generation Backend - Case Study Solution

This repository contains a scalable and robust backend system for an AI image generation service, built as a solution for the Software Engineer case study. The system is implemented entirely in Python using Firebase (Cloud Functions & Firestore) and is designed with best practices for maintainability, testability, and operational excellence.

## Key Features

-   **✅ Atomic Credit Management**: Guarantees financial consistency by handling credit deductions and refunds within atomic Firestore transactions. Users are never charged for failed generations.
-   **🚀 Scalable API & DB Design**: A clean API design coupled with a scalable Firestore schema (e.g., user-specific subcollections for transactions) ensures performance remains high as the user base grows.
-   **🤖 Advanced Weekly Reporting**: A scheduled function automatically generates weekly reports that include not just usage statistics but also **anomaly detection** to proactively identify unusual spikes in usage or failure rates.
-   **🔧 Flexible Configuration**: Key parameters like the AI model's failure rate are managed via environment variables, allowing for easy adjustments without code deployments.
-   **⚙️ Fully Automated Setup & Testing**:
    -   **One-Command Setup**: The entire local environment, including all necessary data, is set up with a single script (`./start-emulator.sh`).
    -   **One-Command Testing**: The entire test suite can be executed with a single script (`./run-tests.sh`), which automatically handles setup, execution, and cleanup.

---

## Quick Start

### Prerequisites

-   [Firebase CLI](https://firebase.google.com/docs/cli#install)
-   [Python 3.10+](https://www.python.org/downloads/)
-   A Java Development Kit (JDK) is required by the Firebase Emulators.

### 1. Installation

Clone the repository to your local machine:
```bash
git clone https://github.com/fuzunist/testing_case.git
cd testing_case
```

### 2. Running the System

To start the complete local environment (Firebase Emulators and Python Functions), run the automated startup script. This single command handles everything, including importing all necessary data.

```bash
./start-emulator.sh
```
The services will be available at:
-   **Emulator UI**: [http://localhost:4000](http://localhost:4000)
-   **Functions API**: `http://127.0.0.1:5001`

### 3. Running the Automated Tests

To verify the entire system's functionality, run the automated test script. This will start the emulators, run all 9 `pytest` tests, report the result, and automatically shut down all services.

```bash
./run-tests.sh
```
You should see a "✅ **SUCCESS: All tests passed!**" message upon completion.

---

## API Usage (`cURL` Examples)

*(The initial data includes two test users: `testUser1` (100 credits) and `testUser2` (10 credits))*

### 1. Create Generation Request

**Note**: Use `"model-a"` or `"model-b"` (lowercase), not "Model A".

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
**Success Response:**
```json
{
    "generationRequestId": "some-unique-id",
    "deductedCredits": 1,
    "imageUrl": "https://.../placeholder-image.png"
}
```

### 2. Get User Credits & History

```bash
curl -X GET "http://127.0.0.1:5001/demo-case-study/us-central1/getUserCredits?userId=testUser1"
```
**Success Response:**
```json
{
    "currentCredits": 99,
    "transactions": [
        {
            "id": "some-tx-id",
            "type": "deduction",
            "credits": 1,
            "generationRequestId": "some-unique-id",
            "timestamp": "2025-08-04T..."
        }
    ]
}
```

---

## Architecture and Design Decisions

This section highlights the key technical decisions made to ensure the system is robust, scalable, and maintainable.

### 1. File Structure

The `functions` directory is structured for clarity and separation of concerns:
-   **`main.py` (Entry Point)**: The entry point for the Functions Framework. It receives all HTTP requests and routes them to the appropriate handler.
-   **`handlers.py` (Business Logic)**: Contains the core application logic for each API endpoint (`createGenerationRequest`, `getUserCredits`, `scheduleWeeklyReport`).
-   **`config.py`**: Centralizes all application configuration.
-   **`ai_simulator.py`**: A module to simulate AI model behavior, including failures.

### 2. Database Schema (Firestore)

-   **`users`**: Stores user data, including their current `credits`.
-   **`transactions` (Subcollection)**: By storing transactions in a subcollection (`/users/{userId}/transactions/{txId}`), we ensure that queries for a user's history remain fast and efficient, regardless of the total number of users or transactions in the system.
-   **`generationRequests`**: A root-level collection to store details of every request.
-   **`reports`**: Stores the output of the weekly reporting function.
-   **Configuration Collections (`styles`, `colors`, `sizes`)**: Storing these as collections makes the system extensible. New options can be added directly to the database without any code changes.

### 3. Core Logic Highlights

-   **Atomicity**: The critical financial operation—deducting credits and creating a request—is performed in a single, atomic Firestore transaction. This guarantees data consistency.
-   **Anomaly Detection**: The weekly report doesn't just aggregate data; it compares the current week's metrics against the *previous week's report* to detect anomalies like a sudden drop in success rate or a spike in usage, which is crucial for operational monitoring.
-   **Environment-Driven Configuration**: Key parameters like the AI's failure rate are controlled by environment variables, following the best practice of separating configuration from code.

---

## Case Study Requirements Checklist

| Requirement                               | Implemented? | Notes                                                                                                                             |
| ----------------------------------------- | :----------: | --------------------------------------------------------------------------------------------------------------------------------- |
| **Credit & Transaction Management**       |      ✅      | Credit deduction and refunds are fully implemented using atomic Firestore transactions.                                           |
| **API: `createGenerationRequest`**        |      ✅      | Endpoint is fully functional, handling validation, credit deduction, simulation, and refunds.                                     |
| **API: `getUserCredits`**                 |      ✅      | Endpoint correctly returns the current balance and a detailed transaction history.                                                |
| **API: `scheduleWeeklyReport`**           |      ✅      | A scheduled function that aggregates data, calculates metrics, and performs anomaly detection.                                    |
| **AI Model Simulation**                   |      ✅      | The `ai_simulator.py` module provides mock generation for two models with a configurable failure rate.                              |
| **Input Validation**                      |      ✅      | The system validates `model`, `style`, `color`, and `size` against values stored in Firestore, rejecting invalid requests.    |
| **Automated Testing**                     |      ✅      | A comprehensive `pytest` suite covers all key business logic, including credits, refunds, validation, and reporting.            |
| **Automated Setup (Emulator Import)**     |      ✅      | All necessary data is exported and automatically imported via the `--import` flag, enabling one-command setup.                    |
| **Comprehensive `README.md`**             |      ✅      | This document provides clear, concise instructions and outlines key architectural decisions.                                        |
