# AI Image Generation Backend System

A scalable and robust AI image generation backend system built with Python, Firebase Functions, and Firestore. Features a credit-based economy with automatic refund logic, comprehensive APIs for image generation and credit management, and automated weekly reporting.

## 🏗️ Technical Architecture

### Backend Technology Stack
- **Runtime**: Python 3.13
- **Cloud Platform**: Firebase Functions
- **Database**: Firebase Firestore
- **Testing**: pytest
- **Local Development**: Firebase Local Emulator Suite

### System Components

#### 1. Database Schema (Firestore Collections)

**Users Collection (`users`)**
- Document ID: `userId`
- Fields: `credits` (Number)

**Users Transactions Subcollection (`users/{userId}/transactions`)**
- Document ID: Auto-generated
- Fields:
  - `type` (String): "deduction" or "refund"
  - `credits` (Number): Amount of credits
  - `generationRequestId` (String): Reference to generation request
  - `timestamp` (Timestamp): Transaction time

**Generation Requests Collection (`generationRequests`)**
- Document ID: Auto-generated
- Fields:
  - `userId` (String): User identifier
  - `model` (String): "Model A" or "Model B"
  - `style` (String): Image style (realistic, anime, oil painting, sketch, cyberpunk, watercolor)
  - `color` (String): Color scheme (vibrant, monochrome, pastel, neon, vintage)
  - `size` (String): Image dimensions (512x512, 1024x1024, 1024x1792)
  - `prompt` (String): User's text prompt
  - `status` (String): "pending", "completed", or "failed"
  - `imageUrl` (String): Generated image URL (on success)
  - `cost` (Number): Credits deducted for this request
  - `createdAt` (Timestamp): Request creation time

**Configuration Collections**
- **Styles** (`styles`): Valid style options
- **Colors** (`colors`): Valid color options  
- **Sizes** (`sizes`): Valid size options with associated credit costs

**Reports Collection (`reports`)**
- Document ID: Date in YYYY-MM-DD format
- Fields: Weekly aggregated usage statistics

#### 2. Credit System

**Credit Costs by Image Size:**
- 512x512: 1 credit
- 1024x1024: 3 credits
- 1024x1792: 4 credits

**Transaction Flow:**
1. **Deduction**: Credits are atomically deducted when request is created
2. **Generation**: AI model simulation (95% success rate, 5% failure)
3. **Completion**: On success, request marked complete with image URL
4. **Refund**: On failure, credits automatically refunded and transaction logged

#### 3. AI Model Simulation

- **Model A**: Returns placeholder URL: `https://storage.googleapis.com/ai-image-gen-backend.appspot.com/placeholders/model_a_placeholder.jpg`
- **Model B**: Returns placeholder URL: `https://storage.googleapis.com/ai-image-gen-backend.appspot.com/placeholders/model_b_placeholder.jpg`
- **Failure Rate**: Configurable 5% failure rate for testing refund logic

## 🚀 Setup Instructions

### Prerequisites
- Node.js (for Firebase CLI)
- Python 3.13+
- Git

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai-image-generation-backend
```

### 2. Install Firebase CLI
```bash
npm install -g firebase-tools
```

### 3. Set Up Python Environment
```bash
cd functions
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Firebase Project Setup (Optional)
For local development, you can skip Firebase project creation and use the demo project:
```bash
# Login to Firebase (optional for local development)
firebase login

# For production deployment only:
firebase use --add  # Select your Firebase project
```

## 🏃‍♂️ Running the Project

### Start the Local Emulator
```bash
firebase emulators:start --import=./initial_data
```

This command:
- Starts Firestore emulator on port 8080
- Starts Functions emulator on port 5001
- Starts Emulator UI on port 4000
- Imports pre-configured initial data

### Access Points
- **Emulator UI**: http://localhost:4000
- **Firestore Emulator**: http://localhost:8080
- **Functions Base URL**: http://localhost:5001/demo-project/us-central1

## 🧪 Running Tests

### Execute Full Test Suite
```bash
# From project root directory
pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Test credit deduction logic
pytest tests/test_credit_deduction.py -v

# Test insufficient funds scenarios
pytest tests/test_insufficient_funds.py -v

# Test refund functionality
pytest tests/test_refund_on_failure.py -v

# Test input validation
pytest tests/test_input_validation.py -v

# Test user credits API
pytest tests/test_get_user_credits.py -v

# Test weekly reporting
pytest tests/test_weekly_report.py -v
```

### Test Coverage
The test suite covers:
- ✅ Credit deduction and balance verification
- ✅ Insufficient funds handling
- ✅ Automatic refund on generation failure
- ✅ Input validation for all parameters
- ✅ Transaction history tracking
- ✅ Weekly report generation and statistics
- ✅ API error handling and edge cases

## 📡 API Documentation

### 1. Create Generation Request

**Endpoint**: `POST /createGenerationRequest`

**Request Body:**
```json
{
  "userId": "testUser1",
  "model": "Model A",
  "style": "realistic",
  "color": "vibrant", 
  "size": "1024x1024",
  "prompt": "A beautiful landscape"
}
```

**Success Response (201):**
```json
{
  "generationRequestId": "abc123",
  "deductedCredits": 3,
  "imageUrl": "https://storage.googleapis.com/ai-image-gen-backend.appspot.com/placeholders/model_a_placeholder.jpg"
}
```

**Error Responses:**
- **400 Bad Request**: Invalid input parameters
  ```json
  {"error": "Invalid style: invalid_style"}
  ```
- **402 Payment Required**: Insufficient credits
  ```json
  {"error": "Insufficient credits"}
  ```
- **404 Not Found**: User not found
  ```json
  {"error": "User not found"}
  ```
- **500 Internal Server Error**: Generation failure (with refund)
  ```json
  {"error": "AI generation failed, credits have been refunded."}
  ```

### 2. Get User Credits

**Endpoint**: `GET /getUserCredits?userId={userId}`

**Example Request:**
```
GET /getUserCredits?userId=testUser1
```

**Success Response (200):**
```json
{
  "currentCredits": 97,
  "transactions": [
    {
      "id": "trans123",
      "type": "deduction",
      "credits": 3,
      "generationRequestId": "req456",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Error Responses:**
- **400 Bad Request**: Missing userId parameter
- **404 Not Found**: User not found

### 3. Weekly Report (Scheduled Function)

**Trigger**: Automatic - Every Monday at 9:00 AM UTC

**Function**: `scheduleWeeklyReport`

**Generated Report Structure:**
```json
{
  "startDate": "2024-01-08T00:00:00Z",
  "endDate": "2024-01-15T00:00:00Z", 
  "modelStats": {
    "Model A": {"success": 15, "failure": 1},
    "Model B": {"success": 8, "failure": 0}
  },
  "styleStats": {
    "realistic": {"count": 12},
    "anime": {"count": 8}
  },
  "sizeStats": {
    "512x512": {"count": 5},
    "1024x1024": {"count": 10},
    "1024x1792": {"count": 8}
  },
  "totalCreditsSpent": 67,
  "totalCreditsRefunded": 3
}
```

## 🗃️ Initial Data

The system includes pre-configured test data:

### Test Users
- **testUser1**: 100 credits
- **testUser2**: 10 credits

### Valid Options
- **Models**: Model A, Model B
- **Styles**: realistic, anime, oil painting, sketch, cyberpunk, watercolor
- **Colors**: vibrant, monochrome, pastel, neon, vintage
- **Sizes**: 512x512 (1 credit), 1024x1024 (3 credits), 1024x1792 (4 credits)

## 🔧 Development Features

### Error Handling
- Comprehensive input validation
- Atomic transaction operations
- Automatic credit refunds on failures
- Graceful error responses with descriptive messages

### Testing Infrastructure
- Isolated test environment with emulator
- Automatic data reset between tests
- Mocking for AI generation simulation
- Comprehensive test coverage

### Monitoring & Reporting
- Weekly automated reports
- Usage statistics by model, style, and size
- Credit consumption tracking
- Success/failure rate analysis

## 🚀 Deployment (Optional)

### Deploy to Firebase
```bash
firebase deploy --only functions
```

### Environment Variables
For production deployment, configure:
- Firebase project settings
- Authentication rules
- Security rules for Firestore

## 🏗️ Architecture Decisions

### Database Design
- **Subcollections**: Transaction history stored as subcollections for better scalability
- **Atomic Operations**: Firestore transactions ensure data consistency
- **Denormalization**: Configuration data stored for fast validation

### Credit System
- **Upfront Deduction**: Credits deducted immediately to prevent race conditions
- **Automatic Refunds**: Failed generations trigger immediate refunds
- **Audit Trail**: Complete transaction history for transparency

### Error Handling
- **Graceful Degradation**: System continues operation even with partial failures
- **User-Friendly Messages**: Clear error descriptions for debugging
- **Rollback Mechanisms**: Failed operations are completely reversed

## 📊 System Monitoring

The weekly reporting system provides insights into:
- Usage patterns by AI model
- Popular styles and image sizes  
- Credit consumption trends
- System reliability metrics
- User behavior analytics

## 🔐 Security Considerations

- Input validation prevents malicious requests
- Firestore security rules can be configured for production
- Credit system prevents unauthorized usage
- Transaction logging enables audit capabilities

---

**Built with ❤️ for scalable AI image generation**