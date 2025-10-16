import os
import sys
from flask import Flask, jsonify

# Adiciona o diretório raiz ao sys.path para que possamos encontrar nossos módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import get_all_created_routes

# Inicializa a aplicação Flask
app = Flask(__name__)

# --- ENDPOINTS DA API ---

@app.route('/api/routes', methods=['GET'])
def get_routes():
    """
    Endpoint para buscar todas as rotas criadas.
    O front-end do painel do gestor chamará esta URL para exibir as rotas.
    """
    try:
        # Usa a função que já tínhamos para buscar os dados no banco
        routes = get_all_created_routes()
        # O jsonify converte nossa lista de rotas para o formato JSON, que o front-end entende
        return jsonify(routes), 200
    except Exception as e:
        # Retorna uma mensagem de erro em formato JSON
        return jsonify({"error": "Ocorreu um erro ao buscar as rotas", "details": str(e)}), 500

# O bloco if __name__ == '__main__' foi removido.
# O Gunicorn (servidor de produção) iniciará a aplicação 'app' diretamente.

