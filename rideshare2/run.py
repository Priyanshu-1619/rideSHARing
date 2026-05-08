"""
NextRide — Launch script
Run from the project root: python run.py
For production on Render, use: gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Point Flask to the correct template/static folders (project-root level)
import flask
_orig_flask = flask.Flask.__init__

def _patched_init(self, *args, **kwargs):
    kwargs.setdefault('template_folder', os.path.join(os.path.dirname(__file__), 'templates'))
    kwargs.setdefault('static_folder',   os.path.join(os.path.dirname(__file__), 'static'))
    _orig_flask(self, *args, **kwargs)

flask.Flask.__init__ = _patched_init

from app import app, init_db, USE_MYSQL

if __name__ == '__main__':
    if not USE_MYSQL:
        init_db()
    
    # Get port from environment (Render sets this), default to 8080 for local dev
    port = int(os.environ.get('PORT', 8080))
    
    # Check if running in production
    is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER') == 'true'
    
    print(f"\n🚗 NextRide is running at http://0.0.0.0:{port}\n")
    
    # Use debug mode only in development
    app.run(debug=not is_production, port=port, host="0.0.0.0")
