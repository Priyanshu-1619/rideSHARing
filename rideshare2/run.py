"""
NextRide — Launch script
Run from the project root: python run.py
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
    print("\n🚗 NextRide is running at http://localhost:5000\n")
    app.run(debug=True, port=5000, host="127.0.0.1")
