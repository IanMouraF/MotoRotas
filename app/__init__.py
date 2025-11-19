from flask import Flask
# 1. Adicione este import
from app.database.manager import setup_database 

def create_app():
    app = Flask(__name__)
    
    # 2. Adicione esta chamada ANTES de registrar as rotas
    # Isso garante que as tabelas existem antes de qualquer coisa tentar acessá-las
    setup_database()
    
    # Importa e registra as rotas
    from app.routes import api_bp
    app.register_blueprint(api_bp)
    
    return app