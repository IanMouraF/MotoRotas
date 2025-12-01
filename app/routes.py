import os
import sys
from flask import Blueprint, jsonify

# Ajuste de import para a nova estrutura
from app.database.manager import get_all_created_routes

# Criação do Blueprint (em vez de app = Flask)
api_bp = Blueprint('api', __name__)

# --- ENDPOINTS DA API ---

@api_bp.route('/api/routes', methods=['GET'])
def get_routes():
    """Endpoint para buscar todas as rotas criadas."""
    try:
        routes = get_all_created_routes()
        return jsonify(routes), 200
    except Exception as e:
        return jsonify({"error": "Ocorreu um erro ao buscar as rotas", "details": str(e)}), 500

# Nota: Removemos o bloco "if __name__ == '__main__':" daqui, 
# pois ele agora vive no run.py na raiz do projeto.