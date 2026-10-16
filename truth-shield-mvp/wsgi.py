"""
WSGI configuration for deploying Truth Shield on PythonAnywhere or WSGI servers.
"""
import sys
import os

# Determine project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import the Flask application instance (must be named 'application' for WSGI)
from app import app as application

if __name__ == "__main__":
    application.run()
