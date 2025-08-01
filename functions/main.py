import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from flask import Request
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_functions import https_fn, options
from firebase_functions.scheduler_fn import on_schedule, ScheduledEvent

from ai_simulator import AIChat
from config import ImageModels, AnomalyThresholds

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

options.set_global_options(max_instances=10)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    logger.info("Initializing Firebase Admin SDK with default credentials")
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized successfully")

db = firestore.client()
logger.info("Firestore client initialized")

# Data for validation and cost calculation
try:
    logger.info("Loading initial data from Firestore collections...")
    STYLES = {doc.id for doc in db.collection("styles").stream()}
    COLORS = {doc.id for doc in db.collection("colors").stream()}
    SIZES = {doc.id: doc.to_dict()["credits"] for doc in db.collection("sizes").stream()}
    logger.info(f"Successfully loaded initial data - Styles: {len(STYLES)}, Colors: {len(COLORS)}, Sizes: {len(SIZES)}")
    logger.debug(f"Available styles: {STYLES}")
    logger.debug(f"Available colors: {COLORS}")
    logger.debug(f"Available sizes and costs: {SIZES}")
except Exception as e:
    logger.critical(f"Could not load initial data from Firestore: {e}", exc_info=True)
    STYLES, COLORS, SIZES = set(), set(), {}


@https_fn.on_request()
def createGenerationRequest(req: https_fn.Request) -> https_fn.Response:
    """
    Handles AI image generation requests, manages credits, and simulates generation.
    """
    logger.info("=== Starting createGenerationRequest function ===")
    
    # 1. Extract and Validate Input
    try:
        data = req.get_json()
        logger.info(f"Received request data: {data}")
    except Exception as e:
        logger.error(f"Failed to parse JSON request body: {e}")
        return https_fn.Response("Invalid JSON in request body.", status=400)
    
    user_id = data.get("userId")
    model = data.get("model")
    style = data.get("style")
    color = data.get("color")
    size = data.get("size")
    prompt = data.get("prompt") # Optional but good to have

    logger.info(f"Request parameters - User: {user_id}, Model: {model}, Style: {style}, Color: {color}, Size: {size}, Prompt: {prompt}")

    # Validate required fields
    if not all([user_id, model, style, color, size]):
        missing_fields = []
        if not user_id: missing_fields.append("userId")
        if not model: missing_fields.append("model")
        if not style: missing_fields.append("style")
        if not color: missing_fields.append("color")
        if not size: missing_fields.append("size")
        logger.warning(f"Missing required fields: {missing_fields}")
        return https_fn.Response(f"Missing required fields: {missing_fields}", status=400)

    # Validate style, color, and size
    if style not in STYLES:
        logger.warning(f"Invalid style '{style}'. Available styles: {STYLES}")
        return https_fn.Response(f"Invalid style '{style}'. Available styles: {list(STYLES)}", status=400)
    
    if color not in COLORS:
        logger.warning(f"Invalid color '{color}'. Available colors: {COLORS}")
        return https_fn.Response(f"Invalid color '{color}'. Available colors: {list(COLORS)}", status=400)
    
    if size not in SIZES:
        logger.warning(f"Invalid size '{size}'. Available sizes: {list(SIZES.keys())}")
        return https_fn.Response(f"Invalid size '{size}'. Available sizes: {list(SIZES.keys())}", status=400)
    
    if model not in [ImageModels.model_a.value, ImageModels.model_b.value]:
        logger.warning(f"Invalid model '{model}'. Available models: {[ImageModels.model_a.value, ImageModels.model_b.value]}")
        return https_fn.Response(f"Invalid model '{model}'. Please use one of {[ImageModels.model_a.value, ImageModels.model_b.value]}", status=400)

    logger.info("Input validation passed successfully")

    # 2. Calculate Credit Cost and Verify User
    credit_cost = SIZES[size]
    logger.info(f"Credit cost for size '{size}': {credit_cost}")
    
    user_ref = db.collection("users").document(user_id)
    logger.info(f"Checking if user '{user_id}' exists...")

    # Check if the user exists before proceeding
    user_snapshot = user_ref.get()
    if not user_snapshot.exists:
        logger.warning(f"User '{user_id}' not found in database")
        return https_fn.Response("User not found.", status=404)

    logger.info(f"User '{user_id}' found, proceeding with transaction")

    # 3. Firestore Transaction for Atomic Operation
    try:
        generation_ref = db.collection("generationRequests").document()
        logger.info(f"Created generation request reference: {generation_ref.id}")

        # Run the transaction by passing the transaction function and its arguments
        logger.info("Starting atomic transaction for credit deduction and generation...")
        image_url = _atomic_deduct_and_generate(
            transaction=db.transaction(),
            user_ref=user_ref,
            credit_cost=credit_cost,
            generation_ref=generation_ref,
            data=data,
        )

        logger.info(f"Transaction completed successfully. Image URL: {image_url}")

        # 4. Return Success Response
        response_data = {
            "generationRequestId": generation_ref.id,
            "deductedCredits": credit_cost,
            "imageUrl": image_url,
        }
        logger.info(f"Returning success response: {response_data}")
        return https_fn.Response(
            json.dumps(response_data),
            status=200,
            mimetype="application/json"
        )

    except https_fn.HttpsError as e:
        # Handle specific, known errors (e.g., insufficient funds)
        logger.warning(f"Handled HttpsError for user '{user_id}': {e.message} (code: {e.code})")
        return https_fn.Response(e.message, status=e.code)
    except Exception as e:
        # Handle other potential, unexpected errors
        logger.error(f"Unexpected error in createGenerationRequest for user '{user_id}': {e}", exc_info=True)
        return https_fn.Response("An unexpected internal error occurred.", status=500)


@firestore.transactional
def _atomic_deduct_and_generate(transaction, user_ref, credit_cost, generation_ref, data):
    """
    Atomically deducts credits, creates records, and handles generation simulation.
    """
    logger.info("=== Starting atomic transaction ===")
    
    # 1. Get user data and check credits
    logger.info(f"Getting user data for user ID: {user_ref.id}")
    user_snapshot = user_ref.get(transaction=transaction)
    if not user_snapshot.exists:
        logger.error(f"User '{user_ref.id}' not found during transaction")
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.NOT_FOUND, message="User not found."
        )

    current_credits = user_snapshot.get("credits")
    logger.info(f"Current credits for user '{user_ref.id}': {current_credits}, Required: {credit_cost}")
    
    if current_credits < credit_cost:
        logger.warning(f"Insufficient credits for user '{user_ref.id}'. Current: {current_credits}, Required: {credit_cost}")
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
            message="Insufficient credits.",
        )

    # 2. Deduct credits
    new_credits = current_credits - credit_cost
    logger.info(f"Deducting {credit_cost} credits from user '{user_ref.id}'. New balance: {new_credits}")
    transaction.update(user_ref, {"credits": firestore.Increment(-credit_cost)})

    # 3. Create generation request record (initially pending)
    generation_data = {
        **data,
        "cost": credit_cost,
        "status": "pending",
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    logger.info(f"Creating generation request record with data: {generation_data}")
    transaction.set(generation_ref, generation_data)

    # 4. Log the deduction transaction
    trans_ref = user_ref.collection("transactions").document()
    transaction_log = {
        "type": "deduction",
        "credits": credit_cost,
        "generationRequestId": generation_ref.id,
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    logger.info(f"Logging deduction transaction: {transaction_log}")
    transaction.set(trans_ref, transaction_log)

    logger.info("Atomic transaction completed successfully")

    # --- This part is outside the atomic read/write but part of the function flow ---
    
    # 5. Trigger AI simulation
    logger.info(f"Starting AI simulation for model: {data['model']}")
    model_enum = next((m for m in ImageModels if m.value == data["model"]), None)
    ai_model = AIChat(model=model_enum)
    generation_result = ai_model.create()
    logger.info(f"AI simulation result: {generation_result}")

    # 6. Handle generation result
    if generation_result["success"]:
        # Update request on success
        logger.info(f"AI generation successful, updating request status to 'completed'")
        update_data = {
            "status": "completed",
            "imageUrl": generation_result["imageUrl"],
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        logger.info(f"Updating generation request with: {update_data}")
        db.collection("generationRequests").document(generation_ref.id).update(update_data)
        return generation_result["imageUrl"]
    else:
        # Refund credits on failure
        logger.warning(f"AI generation failed, initiating credit refund for user '{user_ref.id}'")
        _refund_credits(user_ref.id, generation_ref.id, credit_cost)
        
        update_data = {"status": "failed", "updatedAt": firestore.SERVER_TIMESTAMP}
        logger.info(f"Updating generation request status to 'failed': {update_data}")
        db.collection("generationRequests").document(generation_ref.id).update(update_data)
        
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INTERNAL,
            message="AI generation failed, credits refunded.",
        )


def _refund_credits(user_id, generation_id, amount):
    """
    Refunds credits to a user and logs the transaction.
    This runs in its own transaction.
    """
    logger.info(f"=== Starting credit refund process ===")
    logger.info(f"Refunding {amount} credits to user '{user_id}' for generation '{generation_id}'")
    
    user_ref = db.collection("users").document(user_id)
    
    # Note: The generation request status update was moved to the caller
    # to keep this function focused on the transactional refund part.

    # Create a new transaction for the refund
    transaction = db.transaction()
    
    @firestore.transactional
    def refund_transaction(trans, ref, cost):
        logger.info(f"Executing refund transaction for user '{ref.id}'")
        
        # Get current credits before refund
        user_snapshot = ref.get(transaction=trans)
        if user_snapshot.exists:
            current_credits = user_snapshot.get("credits")
            new_credits = current_credits + cost
            logger.info(f"Current credits: {current_credits}, Adding: {cost}, New total: {new_credits}")
        else:
            logger.error(f"User '{ref.id}' not found during refund transaction")
            raise Exception(f"User '{ref.id}' not found during refund")
        
        trans.update(ref, {"credits": firestore.Increment(cost)})
        
        # Log the refund transaction
        refund_trans_ref = ref.collection("transactions").document()
        refund_log = {
            "type": "refund",
            "credits": cost,
            "generationRequestId": generation_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
        logger.info(f"Logging refund transaction: {refund_log}")
        trans.set(refund_trans_ref, refund_log)

    try:
        refund_transaction(transaction, user_ref, amount)
        logger.info(f"Credit refund completed successfully for user '{user_id}'")
    except Exception as e:
        logger.error(f"Failed to refund credits for user '{user_id}': {e}", exc_info=True)
        raise


@https_fn.on_request()
def getUserCredits(req: https_fn.Request) -> https_fn.Response:
    """
    Retrieves a user's current credit balance and transaction history.
    """
    logger.info("=== Starting getUserCredits function ===")
    
    # 1. Extract and Validate userId
    user_id = req.args.get("userId")
    logger.info(f"Request for user credits - User ID: {user_id}")
    
    if not user_id:
        logger.warning("getUserCredits called without userId parameter")
        return https_fn.Response("userId parameter is required.", status=400)

    try:
        # 2. Get User Document
        logger.info(f"Fetching user document for user '{user_id}'")
        user_ref = db.collection("users").document(user_id)
        user_snapshot = user_ref.get()

        if not user_snapshot.exists:
            logger.warning(f"User '{user_id}' not found in database")
            return https_fn.Response("User not found.", status=404)

        # 3. Get Current Credits
        current_credits = user_snapshot.get("credits")
        logger.info(f"Current credits for user '{user_id}': {current_credits}")

        # 4. Get Transaction History
        logger.info(f"Fetching transaction history for user '{user_id}'")
        transactions_ref = user_ref.collection("transactions").order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).stream()

        transactions = []
        transaction_count = 0
        for trans in transactions_ref:
            trans_data = trans.to_dict()
            transaction_info = {
                "id": trans.id,
                "type": trans_data.get("type"),
                "credits": trans_data.get("credits"),
                "generationRequestId": trans_data.get("generationRequestId"),
                "timestamp": trans_data.get("timestamp").isoformat(),
            }
            transactions.append(transaction_info)
            transaction_count += 1

        logger.info(f"Retrieved {transaction_count} transactions for user '{user_id}'")

        # 5. Return Response
        response_data = {
            "currentCredits": current_credits,
            "transactions": transactions,
        }
        logger.info(f"Returning credit information for user '{user_id}': {response_data}")
        return https_fn.Response(
            json.dumps(response_data),
            status=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Unexpected error in getUserCredits for user '{user_id}': {e}", exc_info=True)
        return https_fn.Response("An unexpected internal error occurred.", status=500)


@on_schedule(schedule="every monday 00:00")
def scheduleWeeklyReport(event: ScheduledEvent) -> dict:
    """
    Aggregates usage data from the last week, detects anomalies by comparing
    with the previous week's report, and saves it to a 'reports' collection.
    """
    logger.info(f"=== Starting weekly report generation ===")
    logger.info(f"Event details - Job name: {event.job_name}, Schedule: {event.schedule}")

    try:
        # 1. Define the time range for the last week
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)
        logger.info(f"Report period: {one_week_ago} to {now}")

        # 2. Get the latest report from the previous week for anomaly comparison
        logger.info("Fetching previous week's report for anomaly comparison")
        previous_reports_query = db.collection("reports").order_by(
            "generatedAt", direction=firestore.Query.DESCENDING
        ).limit(1).stream()
        previous_report_data = next(
            (report.to_dict() for report in previous_reports_query), None
        )
        
        if previous_report_data:
            logger.info("Found previous report for comparison")
        else:
            logger.info("No previous report found - this may be the first report")

        # 3. Get all generation requests from the last 7 days
        logger.info("Fetching generation requests from the last 7 days")
        requests_ref = db.collection("generationRequests").where(
            "createdAt", ">=", one_week_ago
        ).stream()

        report = {
            "totalRequests": 0,
            "totalCreditsSpent": 0,
            "totalCreditsRefunded": 0,
            "successRate": 0,
            "byModel": {},
            "byStyle": {},
            "bySize": {},
            "anomalies": []
        }

        # 4. Aggregate Data
        successful_requests = 0
        request_count = 0
        
        for req in requests_ref:
            data = req.to_dict()
            report["totalRequests"] += 1
            request_count += 1
            
            model = data.get("model", "unknown")
            style = data.get("style", "unknown")
            size = data.get("size", "unknown")
            status = data.get("status", "unknown")
            cost = data.get("cost", 0)

            logger.debug(f"Processing request {request_count}: Model={model}, Style={style}, Size={size}, Status={status}, Cost={cost}")

            # Increment total counts
            if status == "completed":
                report["totalCreditsSpent"] += cost
                successful_requests += 1
            elif status == "failed":
                report["totalCreditsRefunded"] += cost
            
            # Aggregate by model, style, and size
            for key, value in [("byModel", model), ("byStyle", style), ("bySize", size)]:
                if value not in report[key]:
                    report[key][value] = {"total": 0, "completed": 0, "failed": 0, "failureRate": 0}
                
                report[key][value]["total"] += 1
                if status == "completed":
                    report[key][value]["completed"] += 1
                elif status == "failed":
                    report[key][value]["failed"] += 1
        
        logger.info(f"Processed {request_count} generation requests")

        # Calculate success & failure rates
        if report["totalRequests"] > 0:
            report["successRate"] = (successful_requests / report["totalRequests"]) * 100
            logger.info(f"Overall success rate: {report['successRate']:.2f}%")
            
            for group_name, group in [("byModel", report["byModel"]), ("byStyle", report["byStyle"]), ("bySize", report["bySize"])]:
                for item_name, item in group.items():
                    if item["total"] > 0:
                        item["failureRate"] = (item["failed"] / item["total"]) * 100
                        logger.debug(f"{group_name} '{item_name}': {item['total']} total, {item['completed']} completed, {item['failed']} failed, {item['failureRate']:.2f}% failure rate")

        # 5. Detect Anomalies
        logger.info("Detecting anomalies by comparing with previous week")
        if previous_report_data:
            report["anomalies"] = _detect_anomalies(report, previous_report_data)
            logger.info(f"Detected {len(report['anomalies'])} anomalies")
        else:
            report["anomalies"] = ["No previous report available for comparison"]
            logger.info("No previous report available for anomaly detection")

        # 6. Save the report to Firestore
        report_id = f"report_{now.strftime('%Y-%m-%d')}"
        report_ref = db.collection("reports").document(report_id)
        report["generatedAt"] = firestore.SERVER_TIMESTAMP
        
        logger.info(f"Saving report to Firestore with ID: {report_id}")
        report_ref.set(report)

        logger.info(f"Successfully generated and saved weekly report: {report_ref.id}")
        logger.info(f"Report summary - Total requests: {report['totalRequests']}, Success rate: {report['successRate']:.2f}%, Credits spent: {report['totalCreditsSpent']}, Credits refunded: {report['totalCreditsRefunded']}")
        
        return report

    except Exception as e:
        logger.error(f"Error generating weekly report: {e}", exc_info=True)
        raise

def _detect_anomalies(current_metrics: Dict, previous_metrics: Dict) -> List[str]:
    """Compares current metrics against previous metrics to find anomalies."""
    logger.info("=== Starting anomaly detection ===")
    anomalies = []
    
    # Anomaly 1: Significant drop in overall success rate
    prev_success_rate = previous_metrics.get("successRate", 100)
    current_success_rate = current_metrics["successRate"]
    logger.info(f"Comparing success rates - Previous: {prev_success_rate:.2f}%, Current: {current_success_rate:.2f}%")
    
    if prev_success_rate > 0 and \
       current_success_rate < prev_success_rate * AnomalyThresholds.SUCCESS_RATE_DROP_RATIO:
       anomaly_msg = f"Drastic drop in success rate: from {prev_success_rate:.2f}% to {current_success_rate:.2f}%"
       anomalies.append(anomaly_msg)
       logger.warning(f"ANOMALY DETECTED: {anomaly_msg}")

    # Anomaly 2: Unusual spike in total requests
    prev_total_requests = previous_metrics.get("totalRequests", 0)
    current_total_requests = current_metrics["totalRequests"]
    logger.info(f"Comparing total requests - Previous: {prev_total_requests}, Current: {current_total_requests}")
    
    if prev_total_requests > AnomalyThresholds.MIN_SAMPLES_FOR_ANOMALY and \
       current_total_requests > prev_total_requests * AnomalyThresholds.USAGE_SPIKE_MULTIPLIER:
       anomaly_msg = f"Unusual spike in total requests: {current_total_requests} this week vs {prev_total_requests} last week"
       anomalies.append(anomaly_msg)
       logger.warning(f"ANOMALY DETECTED: {anomaly_msg}")

    # Anomaly 3: Unusual spike in credit consumption
    prev_credits_spent = previous_metrics.get("totalCreditsSpent", 0)
    current_credits_spent = current_metrics["totalCreditsSpent"]
    logger.info(f"Comparing credit consumption - Previous: {prev_credits_spent}, Current: {current_credits_spent}")
    
    if prev_credits_spent > AnomalyThresholds.MIN_SAMPLES_FOR_ANOMALY and \
       current_credits_spent > prev_credits_spent * AnomalyThresholds.USAGE_SPIKE_MULTIPLIER:
       anomaly_msg = f"Unusual spike in credit consumption: {current_credits_spent} this week vs {prev_credits_spent} last week"
       anomalies.append(anomaly_msg)
       logger.warning(f"ANOMALY DETECTED: {anomaly_msg}")

    # Anomaly 4: Spike in failure rate for a specific category (model, style, etc.)
    logger.info("Checking for failure rate spikes in specific categories")
    for key in ["byModel", "byStyle", "bySize"]:
        if key in previous_metrics:
            logger.info(f"Analyzing {key} category for anomalies")
            for item_name, current_item_data in current_metrics[key].items():
                previous_item_data = previous_metrics[key].get(item_name)
                if previous_item_data and previous_item_data.get("total", 0) > AnomalyThresholds.MIN_SAMPLES_FOR_ANOMALY:
                    prev_failure_rate = previous_item_data.get("failureRate", 0)
                    current_failure_rate = current_item_data["failureRate"]

                    logger.debug(f"{key} '{item_name}': Previous failure rate: {prev_failure_rate:.2f}%, Current: {current_failure_rate:.2f}%")

                    if current_failure_rate > prev_failure_rate * AnomalyThresholds.FAILURE_RATE_SPIKE_MULTIPLIER and \
                       current_failure_rate > AnomalyThresholds.SIGNIFICANT_FAILURE_RATE:
                        anomaly_msg = f"Spike in failure rate for {key} '{item_name}': {current_failure_rate:.2f}% this week vs {prev_failure_rate:.2f}% last week"
                        anomalies.append(anomaly_msg)
                        logger.warning(f"ANOMALY DETECTED: {anomaly_msg}")
    
    if not anomalies:
        anomalies.append("No significant anomalies detected this week.")
        logger.info("No significant anomalies detected")
    else:
        logger.info(f"Total anomalies detected: {len(anomalies)}")
        
    return anomalies