#!/usr/bin/env python3
"""
Wrapper for Firebase Functions to work with Functions Framework
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all functions from main module
from main import createGenerationRequest, getUserCredits, scheduleWeeklyReport

# Make functions available at module level
__all__ = ['createGenerationRequest', 'getUserCredits', 'scheduleWeeklyReport'] 