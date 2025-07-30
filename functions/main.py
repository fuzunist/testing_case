import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from flask import Request
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_functions import https_fn, options
from firebase_functions.scheduler_fn import on_schedule, ScheduledEvent

from ai_simulator import AIChat, ImageModels

options.set_global_options(max_instances=10)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Data for validation and cost calculation
try:
    STYLES = {doc.id for doc in db.collection("styles").stream()}
    COLORS = {doc.id for doc in db.collection("colors").stream()}
    SIZES = {doc.id: doc.to_dict()["credits"] for doc in db.collection("sizes").stream()}
except Exception as e:
    print(f"Error loading initial data: {e}")
    STYLES, COLORS, SIZES = set(), set(), {}


@https_fn.on_request()
def createGenerationRequest(req: https_fn.Request) -> https_fn.Response:
    """
    Handles AI image generation requests, manages credits, and simulates generation.
    """
    # 1. Extract and Validate Input
    data = req.get_json()
    user_id = data.get("userId")
    model = data.get("model")
    style = data.get("style")
    color = data.get("color")
    size = data.get("size")
    prompt = data.get("prompt") # Optional but good to have

    if not all([user_id, model, style, color, size]):
        return https_fn.Response("Missing required fields.", status=400)

    if style not in STYLES or color not in COLORS or size not in SIZES:
        return https_fn.Response("Invalid style, color, or size.", status=400)
    
    if model not in [ImageModels.model_a.value, ImageModels.model_b.value]:
        return https_fn.Response(f"Invalid model. please use one of {ImageModels.model_a.value, ImageModels.model_b.value}", status=400)

    # 2. Calculate Credit Cost and Verify User
    credit_cost = SIZES[size]
    user_ref = db.collection("users").document(user_id)

    # Check if the user exists before proceeding
    user_snapshot = user_ref.get()
    if not user_snapshot.exists:
        return https_fn.Response("User not found.", status=404)

    # 3. Firestore Transaction for Atomic Operation
    try:
        # The transactional function will handle the transaction creation and commit.
        generation_ref = db.collection("generationRequests").document()

        # Run the transaction
        image_url = _atomic_deduct_and_generate(
            user_ref, credit_cost, generation_ref, data
        )
        
        # 4. Return Success Response
        return https_fn.Response(
            {
                "generationRequestId": generation_ref.id,
                "deductedCredits": credit_cost,
                "imageUrl": image_url,
            }
        )

    except https_fn.HttpsError as e:
        # Handle specific errors (e.g., insufficient funds)
        return https_fn.Response(e.message, status=e.code)
    except Exception as e:
        # Handle other potential errors
        return https_fn.Response(f"An unexpected error occurred: {e}", status=500)


@firestore.transactional
def _atomic_deduct_and_generate(transaction, user_ref, credit_cost, generation_ref, data):
    """
    Atomically deducts credits, creates records, and handles generation simulation.
    """
    # 1. Get user data and check credits
    user_snapshot = user_ref.get(transaction=transaction)
    if not user_snapshot.exists:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.NOT_FOUND, message="User not found."
        )

    current_credits = user_snapshot.get("credits")
    if current_credits < credit_cost:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
            message="Insufficient credits.",
        )

    # 2. Deduct credits
    transaction.update(user_ref, {"credits": firestore.Increment(-credit_cost)})

    # 3. Create generation request record (initially pending)
    generation_data = {
        **data,
        "cost": credit_cost,
        "status": "pending",
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    transaction.set(generation_ref, generation_data)

    # 4. Log the deduction transaction
    trans_ref = user_ref.collection("transactions").document()
    transaction.set(
        trans_ref,
        {
            "type": "deduction",
            "credits": credit_cost,
            "generationRequestId": generation_ref.id,
            "timestamp": firestore.SERVER_TIMESTAMP,
        },
    )

    # --- This part is outside the atomic read/write but part of the function flow ---
    
    # 5. Trigger AI simulation
    ai_model = AIChat(model=ImageModels(data["model"]))
    generation_result = ai_model.create()

    # 6. Handle generation result
    if generation_result["success"]:
        # Update request on success
        db.collection("generationRequests").document(generation_ref.id).update(
            {
                "status": "completed",
                "imageUrl": generation_result["imageUrl"],
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )
        return generation_result["imageUrl"]
    else:
        # Refund credits on failure
        _refund_credits(user_ref.id, generation_ref.id, credit_cost)
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INTERNAL,
            message="AI generation failed, credits refunded.",
        )


def _refund_credits(user_id, generation_id, amount):
    """
    Refunds credits to a user and logs the transaction.
    This runs in its own transaction.
    """
    user_ref = db.collection("users").document(user_id)
    
    # Update generation request to "failed"
    db.collection("generationRequests").document(generation_id).update(
        {"status": "failed", "updatedAt": firestore.SERVER_TIMESTAMP}
    )

    # Create a new transaction for the refund
    transaction = db.transaction()
    
    @firestore.transactional
    def refund_transaction(trans, ref, cost):
        trans.update(ref, {"credits": firestore.Increment(cost)})
        # Log the refund transaction
        refund_trans_ref = ref.collection("transactions").document()
        trans.set(
            refund_trans_ref,
            {
                "type": "refund",
                "credits": cost,
                "generationRequestId": generation_id,
                "timestamp": firestore.SERVER_TIMESTAMP,
            },
        )

    refund_transaction(transaction, user_ref, amount)


@https_fn.on_request()
def getUserCredits(req: https_fn.Request) -> https_fn.Response:
    """
    Retrieves a user's current credit balance and transaction history.
    """
    # 1. Extract and Validate userId
    user_id = req.args.get("userId")
    if not user_id:
        return https_fn.Response("userId parameter is required.", status=400)

    try:
        # 2. Get User Document
        user_ref = db.collection("users").document(user_id)
        user_snapshot = user_ref.get()

        if not user_snapshot.exists:
            return https_fn.Response("User not found.", status=404)

        # 3. Get Current Credits
        current_credits = user_snapshot.get("credits")

        # 4. Get Transaction History
        transactions_ref = user_ref.collection("transactions").order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).stream()

        transactions = []
        for trans in transactions_ref:
            trans_data = trans.to_dict()
            transactions.append(
                {
                    "id": trans.id,
                    "type": trans_data.get("type"),
                    "credits": trans_data.get("credits"),
                    "generationRequestId": trans_data.get("generationRequestId"),
                    "timestamp": trans_data.get("timestamp").isoformat(),
                }
            )

        # 5. Return Response
        return https_fn.Response(
            {
                "currentCredits": current_credits,
                "transactions": transactions,
            }
        )

    except Exception as e:
        return https_fn.Response(f"An unexpected error occurred: {e}", status=500)


@on_schedule(schedule="every monday 00:00")
def scheduleWeeklyReport(event: ScheduledEvent) -> dict:
    """
    Aggregates usage data from the last week, detects anomalies by comparing
    with the previous week's report, and saves it to a 'reports' collection.
    """
    print(f"Starting weekly report generation for event: {event.job_name}")

    try:
        # 1. Define the time range for the last week
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)

        # 2. Get the latest report from the previous week for anomaly comparison
        previous_reports_query = db.collection("reports").order_by(
            "generatedAt", direction=firestore.Query.DESCENDING
        ).limit(1).stream()
        previous_report_data = next(
            (report.to_dict() for report in previous_reports_query), None
        )

        # 3. Get all generation requests from the last 7 days
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
        for req in requests_ref:
            data = req.to_dict()
            report["totalRequests"] += 1
            
            model = data.get("model", "unknown")
            style = data.get("style", "unknown")
            size = data.get("size", "unknown")
            status = data.get("status", "unknown")
            cost = data.get("cost", 0)

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
        
        # Calculate success & failure rates
        if report["totalRequests"] > 0:
            report["successRate"] = (successful_requests / report["totalRequests"]) * 100
            for group in report["byModel"], report["byStyle"], report["bySize"]:
                for item in group.values():
                    if item["total"] > 0:
                        item["failureRate"] = (item["failed"] / item["total"]) * 100

        # 5. Detect Anomalies
        if previous_report_data:
            report["anomalies"] = _detect_anomalies(report, previous_report_data)

        # 6. Save the report to Firestore
        report_id = f"report_{now.strftime('%Y-%m-%d')}"
        report_ref = db.collection("reports").document(report_id)
        report["generatedAt"] = firestore.SERVER_TIMESTAMP
        report_ref.set(report)

        print(f"Successfully generated and saved report: {report_ref.id}")
        return report

    except Exception as e:
        print(f"Error generating weekly report: {e}")
        raise

def _detect_anomalies(current_metrics: Dict, previous_metrics: Dict) -> List[str]:
    """Compares current metrics against previous metrics to find anomalies."""
    anomalies = []
    
    # Anomaly 1: Significant drop in overall success rate
    if previous_metrics.get("successRate", 100) > 0 and \
       current_metrics["successRate"] < previous_metrics.get("successRate", 100) * 0.5:
       anomalies.append(
           f"Drastic drop in success rate: from {previous_metrics.get('successRate', 100):.2f}% to {current_metrics['successRate']:.2f}%"
        )

    # Anomaly 2: Unusual spike in total requests
    if previous_metrics.get("totalRequests", 0) > 10 and \
       current_metrics["totalRequests"] > previous_metrics["totalRequests"] * 3:
       anomalies.append(
           f"Unusual spike in total requests: {current_metrics['totalRequests']} this week vs {previous_metrics['totalRequests']} last week."
        )

    # Anomaly 3: Unusual spike in credit consumption
    if previous_metrics.get("totalCreditsSpent", 0) > 10 and \
       current_metrics["totalCreditsSpent"] > previous_metrics["totalCreditsSpent"] * 3:
       anomalies.append(
            f"Unusual spike in credit consumption: {current_metrics['totalCreditsSpent']} this week vs {previous_metrics['totalCreditsSpent']} last week."
        )

    # Anomaly 4: Spike in failure rate for a specific category (model, style, etc.)
    for key in ["byModel", "byStyle", "bySize"]:
        if key in previous_metrics:
            for item_name, current_item_data in current_metrics[key].items():
                previous_item_data = previous_metrics[key].get(item_name)
                if previous_item_data and previous_item_data.get("total", 0) > 10:
                    if current_item_data["failureRate"] > previous_item_data.get("failureRate", 0) * 2 and \
                       current_item_data["failureRate"] > 20: # Only flag if failure rate is significant
                        anomalies.append(
                            f"Spike in failure rate for {key} '{item_name}': {current_item_data['failureRate']:.2f}% this week vs {previous_item_data.get('failureRate', 0):.2f}% last week."
                        )
    
    if not anomalies:
        anomalies.append("No significant anomalies detected this week.")
        
    return anomalies