from app import create_app
from contextlib import contextmanager

@contextmanager
def pipeline_context():
    app = create_app()
    with app.app_context():
        yield
