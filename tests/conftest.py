"""
Configuration file for pytest.
This file is automatically loaded by pytest and allows us to modify Python's import system.
"""
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))