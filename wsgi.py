"""Entry point for a WSGI server: `gunicorn wsgi:app`."""
from vqvz import create_app

app = create_app()
