"""
Root WSGI configuration for deploying Truth Shield on PythonAnywhere.
"""
import sys
import os

# Point to truth-shield-mvp subfolder or current folder
project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "truth-shield-mvp")
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import app as application

if __name__ == "__main__":
    application.run()
