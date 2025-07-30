import pytest
import requests
from datetime import datetime, timedelta
from unittest.mock import patch


def test_weekly_report_generation(firestore_client):
    """Test basic weekly report generation functionality"""
    
    # We need to test the scheduled function directly since it's not an HTTP endpoint
    # Import the function from the main module
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'functions'))
    
    from main import scheduleWeeklyReport
    
    # Create some test data first
    current_time = datetime.now()
    
    # Add some generation requests to the database
    test_requests = [
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vibrant',
            'size': '1024x1024',
            'status': 'completed',
            'cost': 3,
            'createdAt': current_time - timedelta(days=1)  # Yesterday
        },
        {
            'userId': 'testUser1',
            'model': 'Model B',
            'style': 'anime',
            'color': 'neon',
            'size': '512x512',
            'status': 'completed',
            'cost': 1,
            'createdAt': current_time - timedelta(days=2)  # 2 days ago
        },
        {
            'userId': 'testUser2',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vintage',
            'size': '1024x1792',
            'status': 'failed',
            'cost': 4,
            'createdAt': current_time - timedelta(days=3)  # 3 days ago
        }
    ]
    
    # Add test requests to database
    for req in test_requests:
        firestore_client.collection('generationRequests').add(req)
    
    # Call the weekly report function
    result = scheduleWeeklyReport(None)  # Event parameter not used in our implementation
    
    assert result["reportStatus"] == "success"
    
    # Verify report was created
    report_id = (current_time - timedelta(days=7)).strftime('%Y-%m-%d')
    report_doc = firestore_client.collection('reports').document(report_id).get()
    
    assert report_doc.exists
    report_data = report_doc.to_dict()
    
    # Verify report structure
    assert 'modelStats' in report_data
    assert 'styleStats' in report_data
    assert 'sizeStats' in report_data
    assert 'totalCreditsSpent' in report_data
    assert 'totalCreditsRefunded' in report_data
    assert 'startDate' in report_data
    assert 'endDate' in report_data
    
    # Verify model stats
    model_stats = report_data['modelStats']
    assert 'Model A' in model_stats
    assert 'Model B' in model_stats
    
    # Verify style stats
    style_stats = report_data['styleStats']
    assert 'realistic' in style_stats
    assert 'anime' in style_stats
    
    # Verify size stats
    size_stats = report_data['sizeStats']
    assert '1024x1024' in size_stats
    assert '512x512' in size_stats
    assert '1024x1792' in size_stats


def test_weekly_report_empty_data(firestore_client):
    """Test weekly report generation with no data"""
    
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'functions'))
    
    from main import scheduleWeeklyReport
    
    # Call the weekly report function with no data
    result = scheduleWeeklyReport(None)
    
    assert result["reportStatus"] == "success"
    
    # Verify report was created with empty stats
    current_time = datetime.now()
    report_id = (current_time - timedelta(days=7)).strftime('%Y-%m-%d')
    report_doc = firestore_client.collection('reports').document(report_id).get()
    
    assert report_doc.exists
    report_data = report_doc.to_dict()
    
    # Verify empty stats
    assert report_data['totalCreditsSpent'] == 0
    assert report_data['totalCreditsRefunded'] == 0
    assert report_data['modelStats']['Model A']['success'] == 0
    assert report_data['modelStats']['Model A']['failure'] == 0
    assert report_data['modelStats']['Model B']['success'] == 0
    assert report_data['modelStats']['Model B']['failure'] == 0


def test_weekly_report_credit_calculations(firestore_client):
    """Test that credit calculations in weekly report are correct"""
    
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'functions'))
    
    from main import scheduleWeeklyReport
    
    current_time = datetime.now()
    
    # Add test data with known credit amounts
    test_requests = [
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vibrant',
            'size': '1024x1024',
            'status': 'completed',  # Credits spent
            'cost': 3,
            'createdAt': current_time - timedelta(days=1)
        },
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'anime',
            'color': 'neon',
            'size': '1024x1792',
            'status': 'completed',  # Credits spent
            'cost': 4,
            'createdAt': current_time - timedelta(days=2)
        },
        {
            'userId': 'testUser2',
            'model': 'Model B',
            'style': 'sketch',
            'color': 'monochrome',
            'size': '512x512',
            'status': 'failed',  # Credits refunded
            'cost': 1,
            'createdAt': current_time - timedelta(days=3)
        },
        {
            'userId': 'testUser2',
            'model': 'Model B',
            'style': 'cyberpunk',
            'color': 'neon',
            'size': '1024x1024',
            'status': 'failed',  # Credits refunded
            'cost': 3,
            'createdAt': current_time - timedelta(days=4)
        }
    ]
    
    # Add test requests to database
    for req in test_requests:
        firestore_client.collection('generationRequests').add(req)
    
    # Call the weekly report function
    result = scheduleWeeklyReport(None)
    assert result["reportStatus"] == "success"
    
    # Verify credit calculations
    report_id = (current_time - timedelta(days=7)).strftime('%Y-%m-%d')
    report_doc = firestore_client.collection('reports').document(report_id).get()
    report_data = report_doc.to_dict()
    
    # Total credits spent: 3 + 4 = 7 (completed requests)
    assert report_data['totalCreditsSpent'] == 7
    
    # Total credits refunded: 1 + 3 = 4 (failed requests)
    assert report_data['totalCreditsRefunded'] == 4
    
    # Model stats verification
    model_stats = report_data['modelStats']
    assert model_stats['Model A']['success'] == 2  # 2 completed requests
    assert model_stats['Model A']['failure'] == 0  # 0 failed requests
    assert model_stats['Model B']['success'] == 0  # 0 completed requests
    assert model_stats['Model B']['failure'] == 2  # 2 failed requests


def test_weekly_report_time_filtering(firestore_client):
    """Test that weekly report only includes data from the last 7 days"""
    
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'functions'))
    
    from main import scheduleWeeklyReport
    
    current_time = datetime.now()
    
    # Add requests from different time periods
    test_requests = [
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vibrant',
            'size': '1024x1024',
            'status': 'completed',
            'cost': 3,
            'createdAt': current_time - timedelta(days=1)  # Within 7 days
        },
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vibrant',
            'size': '1024x1024',
            'status': 'completed',
            'cost': 3,
            'createdAt': current_time - timedelta(days=6)  # Within 7 days
        },
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vibrant',
            'size': '1024x1024',
            'status': 'completed',
            'cost': 3,
            'createdAt': current_time - timedelta(days=10)  # Outside 7 days - should be excluded
        }
    ]
    
    # Add test requests to database
    for req in test_requests:
        firestore_client.collection('generationRequests').add(req)
    
    # Call the weekly report function
    result = scheduleWeeklyReport(None)
    assert result["reportStatus"] == "success"
    
    # Verify only recent data is included
    report_id = (current_time - timedelta(days=7)).strftime('%Y-%m-%d')
    report_doc = firestore_client.collection('reports').document(report_id).get()
    report_data = report_doc.to_dict()
    
    # Should only count the 2 requests within 7 days (6 credits total)
    assert report_data['totalCreditsSpent'] == 6  # 3 + 3 = 6
    assert report_data['modelStats']['Model A']['success'] == 2  # Only 2 requests counted


def test_weekly_report_style_and_size_aggregation(firestore_client):
    """Test that style and size statistics are correctly aggregated"""
    
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'functions'))
    
    from main import scheduleWeeklyReport
    
    current_time = datetime.now()
    
    # Add requests with various styles and sizes
    test_requests = [
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'vibrant',
            'size': '512x512',
            'status': 'completed',
            'cost': 1,
            'createdAt': current_time - timedelta(days=1)
        },
        {
            'userId': 'testUser1',
            'model': 'Model A',
            'style': 'realistic',
            'color': 'neon',
            'size': '1024x1024',
            'status': 'completed',
            'cost': 3,
            'createdAt': current_time - timedelta(days=2)
        },
        {
            'userId': 'testUser2',
            'model': 'Model B',
            'style': 'anime',
            'color': 'pastel',
            'size': '512x512',
            'status': 'failed',
            'cost': 1,
            'createdAt': current_time - timedelta(days=3)
        }
    ]
    
    # Add test requests to database
    for req in test_requests:
        firestore_client.collection('generationRequests').add(req)
    
    # Call the weekly report function
    result = scheduleWeeklyReport(None)
    assert result["reportStatus"] == "success"
    
    # Verify aggregation
    report_id = (current_time - timedelta(days=7)).strftime('%Y-%m-%d')
    report_doc = firestore_client.collection('reports').document(report_id).get()
    report_data = report_doc.to_dict()
    
    # Style stats
    style_stats = report_data['styleStats']
    assert style_stats['realistic']['count'] == 2  # 2 realistic requests
    assert style_stats['anime']['count'] == 1  # 1 anime request
    
    # Size stats
    size_stats = report_data['sizeStats']
    assert size_stats['512x512']['count'] == 2  # 2 small size requests
    assert size_stats['1024x1024']['count'] == 1  # 1 medium size request