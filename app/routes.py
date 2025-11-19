import os
import sys
import threading
from flask import Flask, jsonify

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import get_all_created_routes
from app.collector import start_collector_loop
from routing.processor import start_processor_loop

app = Flask(__name__)

# --- ENDPOINTS DA API ---

@app.route('/api/routes', methods=['GET'])
def get_routes():
    """Endpoint para buscar todas as rotas criadas."""
    try:
        routes = get_all_created_routes()
        return jsonify(routes), 200
    except Exception as e:
        return jsonify({"error": "Ocorreu um erro ao buscar as rotas", "details": str(e)}), 500

# --- INICIALIZAÇÃO DOS SERVIÇOS DE FUNDO ---

if __name__ != '__main__':
    # Este bloco só é executado quando o Gunicorn (servidor de produção) inicia a app.
    
    print("Iniciando serviços de fundo (Coletor e Processador)...")
    
    # Inicia o Coletor de Pedidos em uma thread separada
    collector_thread = threading.Thread(target=start_collector_loop, daemon=True)
    collector_thread.start()
    
    # Inicia o Processador de Rotas em uma thread separada
    processor_thread = threading.Thread(target=start_processor_loop, daemon=True)
    processor_thread.start()
    
    print("Serviços de fundo iniciados.")

# Bloco para rodar localmente para testes
if __name__ == '__main__':
    # Inicia os serviços de fundo também para testes locais
    print("MODO DE DESENVOLVIMENTO: Iniciando serviços de fundo...")
    collector_thread = threading.Thread(target=start_collector_loop, daemon=True)
    collector_thread.start()
    processor_thread = threading.Thread(target=start_processor_loop, daemon=True)
    processor_thread.start()
    print("Serviços de fundo iniciados.")
    
    app.run(debug=True, port=5000, use_reloader=False) # use_reloader=False é importante para as threads
