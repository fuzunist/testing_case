import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from flask import Request
import firebase_admin
from firebase_admin import firestore
from firebase_functions import https_fn, scheduler_fn
from ai_simulator import simulate_generation

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()


@https_fn.on_request(cors=True)
def createGenerationRequest(req: Request) -> Dict[str, Any]:
    """
    Creates an image generation request with credit management.
    
    Expected JSON payload:
    {
        "userId": str,
        "model": str ("Model A" or "Model B"),
        "style": str,
        "color": str,
        "size": str,
        "prompt": str
    }
    """
    try:
        # Parse request data
        if req.method != 'POST':
            return {"error": "Method not allowed"}, 405
            
        request_json = req.get_json()
        if not request_json:
            return {"error": "Invalid JSON payload"}, 400
        
        # Extract required fields
        user_id = request_json.get('userId')
        model = request_json.get('model')
        style = request_json.get('style')
        color = request_json.get('color')
        size = request_json.get('size')
        prompt = request_json.get('prompt')
        
        # Validate required fields
        if not all([user_id, model, style, color, size, prompt]):
            return {"error": "Missing required fields"}, 400
        
        # Validate model
        if model not in ["Model A", "Model B"]:
            return {"error": "Invalid model. Must be 'Model A' or 'Model B'"}, 400
        
        # Validate style, color, and size exist in collections
        style_doc = db.collection('styles').document(style).get()
        if not style_doc.exists:
            return {"error": f"Invalid style: {style}"}, 400
            
        color_doc = db.collection('colors').document(color).get()
        if not color_doc.exists:
            return {"error": f"Invalid color: {color}"}, 400
            
        size_doc = db.collection('sizes').document(size).get()
        if not size_doc.exists:
            return {"error": f"Invalid size: {size}"}, 400
        
        # Get cost for the size
        size_data = size_doc.to_dict()
        credit_cost = size_data.get('cost', 0)
        
        # Atomic credit deduction transaction
        @firestore.transactional
        def deduct_credits_transaction(transaction):
            # Read user's current credits
            user_ref = db.collection('users').document(user_id)
            user_doc = transaction.get(user_ref)
            
            if not user_doc.exists:
                raise ValueError("User not found")
            
            user_data = user_doc.to_dict()
            current_credits = user_data.get('credits', 0)
            
            if current_credits < credit_cost:
                raise ValueError("Insufficient credits")
            
            # Deduct credits
            new_credits = current_credits - credit_cost
            transaction.update(user_ref, {'credits': new_credits})
            
            # Create deduction transaction record
            transaction_ref = db.collection('users').document(user_id).collection('transactions').document()
            transaction.set(transaction_ref, {
                'type': 'deduction',
                'credits': credit_cost,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            # Create generation request
            request_ref = db.collection('generationRequests').document()
            request_data = {
                'userId': user_id,
                'model': model,
                'style': style,
                'color': color,
                'size': size,
                'prompt': prompt,
                'status': 'pending',
                'cost': credit_cost,
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            transaction.set(request_ref, request_data)
            
            return request_ref.id, transaction_ref.id
        
        # Execute transaction
        transaction = db.transaction()
        try:
            generation_request_id, transaction_id = deduct_credits_transaction(transaction)
            
            # Update transaction record with generation request ID
            db.collection('users').document(user_id).collection('transactions').document(transaction_id).update({
                'generationRequestId': generation_request_id
            })
            
        except ValueError as e:
            if "Insufficient credits" in str(e):
                return {"error": "Insufficient credits"}, 402
            elif "User not found" in str(e):
                return {"error": "User not found"}, 404
            else:
                return {"error": str(e)}, 400
        except Exception as e:
            return {"error": "Transaction failed"}, 500
        
        # Simulate AI generation
        generation_result = simulate_generation(model)
        
        if generation_result["success"]:
            # Update request with success
            db.collection('generationRequests').document(generation_request_id).update({
                'status': 'completed',
                'imageUrl': generation_result['imageUrl']
            })
            
            return {
                "generationRequestId": generation_request_id,
                "deductedCredits": credit_cost,
                "imageUrl": generation_result['imageUrl']
            }, 201
        else:
            # Refund credits on failure
            @firestore.transactional
            def refund_credits_transaction(transaction):
                user_ref = db.collection('users').document(user_id)
                user_doc = transaction.get(user_ref)
                user_data = user_doc.to_dict()
                current_credits = user_data.get('credits', 0)
                
                # Refund credits
                new_credits = current_credits + credit_cost
                transaction.update(user_ref, {'credits': new_credits})
                
                # Create refund transaction record
                refund_transaction_ref = db.collection('users').document(user_id).collection('transactions').document()
                transaction.set(refund_transaction_ref, {
                    'type': 'refund',
                    'credits': credit_cost,
                    'generationRequestId': generation_request_id,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
            
            # Execute refund transaction
            refund_transaction = db.transaction()
            refund_credits_transaction(refund_transaction)
            
            # Update request status to failed
            db.collection('generationRequests').document(generation_request_id).update({
                'status': 'failed'
            })
            
            return {"error": "AI generation failed, credits have been refunded."}, 500
            
    except Exception as e:
        return {"error": f"Internal server error: {str(e)}"}, 500


@https_fn.on_request(cors=True)
def getUserCredits(req: Request) -> Dict[str, Any]:
    """
    Gets user's current credit balance and transaction history.
    
    Expected query parameter: userId
    """
    try:
        if req.method != 'GET':
            return {"error": "Method not allowed"}, 405
            
        user_id = req.args.get('userId')
        if not user_id:
            return {"error": "Missing userId parameter"}, 400
        
        # Get user's current credits
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return {"error": "User not found"}, 404
        
        user_data = user_doc.to_dict()
        current_credits = user_data.get('credits', 0)
        
        # Get transaction history
        transactions_query = (
            db.collection('users')
            .document(user_id)
            .collection('transactions')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
        )
        
        transactions = []
        for doc in transactions_query.stream():
            transaction_data = doc.to_dict()
            transactions.append({
                'id': doc.id,
                'type': transaction_data.get('type'),
                'credits': transaction_data.get('credits'),
                'generationRequestId': transaction_data.get('generationRequestId'),
                'timestamp': transaction_data.get('timestamp')
            })
        
        return {
            "currentCredits": current_credits,
            "transactions": transactions
        }, 200
        
    except Exception as e:
        return {"error": f"Internal server error: {str(e)}"}, 500


@scheduler_fn.on_schedule(schedule="every monday 09:00", timezone="UTC")
def scheduleWeeklyReport(event) -> Dict[str, str]:
    """
    Generates weekly report of usage statistics.
    Runs every Monday at 9:00 AM UTC.
    """
    try:
        # Calculate start date (7 days ago)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Query generation requests from the last week
        requests_query = (
            db.collection('generationRequests')
            .where('createdAt', '>=', start_date)
            .where('createdAt', '<=', end_date)
        )
        
        # Initialize statistics
        model_stats = {"Model A": {"success": 0, "failure": 0}, "Model B": {"success": 0, "failure": 0}}
        style_stats = {}
        size_stats = {}
        total_credits_spent = 0
        total_credits_refunded = 0
        
        # Process each request
        for doc in requests_query.stream():
            request_data = doc.to_dict()
            model = request_data.get('model')
            style = request_data.get('style')
            size = request_data.get('size')
            status = request_data.get('status')
            cost = request_data.get('cost', 0)
            
            # Update model stats
            if model in model_stats:
                if status == 'completed':
                    model_stats[model]['success'] += 1
                    total_credits_spent += cost
                elif status == 'failed':
                    model_stats[model]['failure'] += 1
                    total_credits_refunded += cost
            
            # Update style stats
            if style:
                if style not in style_stats:
                    style_stats[style] = {'count': 0}
                style_stats[style]['count'] += 1
            
            # Update size stats
            if size:
                if size not in size_stats:
                    size_stats[size] = {'count': 0}
                size_stats[size]['count'] += 1
        
        # Create report
        report_data = {
            'startDate': start_date,
            'endDate': end_date,
            'modelStats': model_stats,
            'styleStats': style_stats,
            'sizeStats': size_stats,
            'totalCreditsSpent': total_credits_spent,
            'totalCreditsRefunded': total_credits_refunded,
            'generatedAt': firestore.SERVER_TIMESTAMP
        }
        
        # Save report to Firestore
        report_id = start_date.strftime('%Y-%m-%d')
        db.collection('reports').document(report_id).set(report_data)
        
        print(f"Weekly report generated for {report_id}")
        return {"reportStatus": "success"}
        
    except Exception as e:
        print(f"Error generating weekly report: {str(e)}")
        return {"reportStatus": "error", "error": str(e)}