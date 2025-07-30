#!/usr/bin/env python3
"""
Flask Application Entry Point for EduSmartAI
Main entry point for running the Flask development server.
"""

from app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == '__main__':
    # Run the development server
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        threaded=True
    )
