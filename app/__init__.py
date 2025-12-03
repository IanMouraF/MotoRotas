from flask import Flask
from flask_cors import CORS  # Importe isso
from app.database.manager import setup_database 

def create_app():
    app = Flask(__name__)
    CORS(app) 

    setup_database()

    from app.routes import api_bp
    app.register_blueprint(api_bp)

    return app