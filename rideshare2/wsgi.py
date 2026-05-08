"""
WSGI entry point for Gunicorn (production server)
Used by Render and other production environments
"""
import sys
import os

# Get the directory of this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add backend to path
sys.path.insert(0, os.path.join(current_dir, 'backend'))

# Point Flask to the correct template/static folders
import flask
_orig_flask = flask.Flask.__init__

def _patched_init(self, *args, **kwargs):
    kwargs.setdefault('template_folder', os.path.join(current_dir, 'templates'))
    kwargs.setdefault('static_folder',   os.path.join(current_dir, 'static'))
    _orig_flask(self, *args, **kwargs)

flask.Flask.__init__ = _patched_init

from app import app, init_db, USE_MYSQL

# Initialize database on startup (if using SQLite)
if not USE_MYSQL:
    with app.app_context():
        try:
            init_db()
        except:
            pass  # Database already initialized

if __name__ == '__main__':
    app.run()
