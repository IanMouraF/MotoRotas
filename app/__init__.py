from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Importa e registra as rotas
    from app.routes import api_bp  # Você precisará criar um Blueprint em routes.py
    app.register_blueprint(api_bp)
    
    return app