"""
Functions Framework Wrapper for Firebase Functions

This wrapper makes Firebase Functions compatible with Functions Framework
by adapting the request/response objects.
"""
import json
import logging
from typing import Any, Dict
from flask import Request, Response, make_response

# Import the actual functions from main
import main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FirebaseFunctionsAdapter:
    """Adapter to make Flask Request compatible with Firebase Functions"""
    
    def __init__(self, flask_request: Request):
        self.path = flask_request.path
        self.method = flask_request.method
        self.args = flask_request.args
        self.headers = flask_request.headers
        self._flask_request = flask_request
        self._json = None
    
    def get_json(self):
        """Get JSON data from request"""
        if self._json is None:
            self._json = self._flask_request.get_json(silent=True)
        return self._json
    
    @property
    def json(self):
        return self.get_json()

def adapt_response(firebase_response):
    """Convert Firebase Functions Response to Flask Response"""
    if hasattr(firebase_response, '_body') and hasattr(firebase_response, '_status'):
        # It's a Firebase Response object
        body = firebase_response._body
        status = firebase_response._status
        
        # Try to parse JSON if it's a string
        if isinstance(body, str):
            try:
                body = json.loads(body)
                return make_response(json.dumps(body), status)
            except:
                return make_response(body, status)
        
        return make_response(json.dumps(body), status)
    
    # Already a Flask response
    return firebase_response

def handle_request(request: Request) -> Response:
    """Main entry point for Functions Framework"""
    try:
        logger.info(f"Request received: {request.method} {request.path}")
        
        # Handle root path
        if request.path == "/" or request.path == "":
            return make_response(json.dumps({
                "message": "AI Image Generation Backend API",
                "version": "1.0.0",
                "available_endpoints": [
                    "/demo-case-study/us-central1/createGenerationRequest",
                    "/demo-case-study/us-central1/getUserCredits",
                    "/demo-case-study/us-central1/scheduleWeeklyReport"
                ]
            }), 200)
        
        # Extract function name from path
        path_parts = request.path.strip('/').split('/')
        
        if len(path_parts) >= 3:
            function_name = path_parts[2]
            logger.info(f"Routing to function: {function_name}")
            
            # Create adapted request
            adapted_request = FirebaseFunctionsAdapter(request)
            
            try:
                if function_name == "createGenerationRequest":
                    # Call the wrapped function directly
                    response = main.createGenerationRequest._function(adapted_request)
                    return adapt_response(response)
                    
                elif function_name == "getUserCredits":
                    # Call the wrapped function directly
                    response = main.getUserCredits._function(adapted_request)
                    return adapt_response(response)
                    
                elif function_name == "scheduleWeeklyReport":
                    # For testing purposes, allow manual trigger
                    class DummyEvent:
                        def __init__(self):
                            self.job_name = "manual-trigger"
                            self.schedule = "manual"
                    
                    result = main.scheduleWeeklyReport(DummyEvent())
                    return make_response(json.dumps(result, default=str), 200)
                    
                else:
                    logger.warning(f"Unknown function name: {function_name}")
                    return make_response(f"Unknown function: {function_name}", 404)
                    
            except Exception as e:
                logger.error(f"Error handling {function_name}: {str(e)}", exc_info=True)
                return make_response(json.dumps({"error": str(e)}), 500)
                
        else:
            logger.warning(f"Invalid path format: {request.path}")
            return make_response("Invalid path format", 400)
            
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return make_response("An unexpected internal error occurred.", 500)

# Main function for Functions Framework
def main(request: Request) -> Response:
    """Entry point for Functions Framework"""
    return handle_request(request) 