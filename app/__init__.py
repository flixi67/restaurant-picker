from flask import Flask
import os
from app.models import db

print("✅ app/__init__.py is being loaded")

def create_app():
    app = Flask(__name__)
    db_path = os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', ''), 'database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from app.routes import pipeline_bp
    from app.routes import main_bp
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(main_bp)

    # Ensure tables are created when the app starts
    with app.app_context():
        # Need to check if this overwrites existing tables
        db.create_all()  # Create tables for all models

    return app
