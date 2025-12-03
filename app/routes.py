import os
import sys
from flask import Blueprint, jsonify, request

# Importa as funções do banco de dados
from app.database.manager import (
    get_all_created_routes, 
    create_motoboy, 
    get_all_motoboys, 
    assign_route_to_motoboy,
    get_route_by_id,
    update_motoboy_status,
    remove_order_from_route, 
    add_order_to_route, 
    update_route, 
    get_route_by_id,
    update_route_status_db,
    unassign_route_from_motoboy
)

from app.routing.optimizer import reorder_route, create_google_maps_link

RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

api_bp = Blueprint('api', __name__)

def recalculate_route_details(route_id):
    """Função auxiliar para reordenar a rota e atualizar o link após mudanças."""
    route = get_route_by_id(route_id)
    if not route or not route['orders']:
        return # Rota vazia ou inexistente
    
    # 1. Reordena matematicamente (Vizinho mais próximo)
    optimized_orders = reorder_route(route['orders'], RESTAURANT_COORDS)
    
    # 2. Gera novo link
    new_link = create_google_maps_link(RESTAURANT_COORDS, optimized_orders)
    
    # 3. Salva no banco (A função update_route já espera esse formato)
    route_data = {
        'id': route_id,
        'orders': optimized_orders,
        'google_maps_link': new_link
    }
    update_route(route_data)

@api_bp.route('/api/orders/move', methods=['POST'])
def move_order():
    """
    Move um pedido de uma rota para outra (ou para nenhuma).
    Ex JSON: { "order_id": "123", "old_route_id": 1, "new_route_id": 2 }
    """
    data = request.json
    order_id = data.get('order_id')
    old_route_id = data.get('old_route_id')
    new_route_id = data.get('new_route_id') # Se for None, apenas remove da rota
    
    if not order_id or not old_route_id:
        return jsonify({"error": "Parâmetros obrigatórios faltando"}), 400

    # LÓGICA CORRIGIDA:
    # Se tiver nova rota -> status volta pra 'routed' (a função add_order faz isso)
    # Se NÃO tiver nova rota -> status vira 'unassigned' (para o processador ignorar)
    target_status = 'pending' if new_route_id else 'unassigned'

    # 1. Remove da rota antiga
    if not remove_order_from_route(old_route_id, order_id, new_status=target_status):
        return jsonify({"error": "Erro ao remover da rota antiga"}), 500
    
    recalculate_route_details(old_route_id)
    
    # 2. Adiciona na rota nova (se houver)
    if new_route_id:
        if not add_order_to_route(new_route_id, order_id):
            return jsonify({"error": "Erro ao adicionar na rota nova"}), 500
        
        recalculate_route_details(new_route_id)
        
    return jsonify({"message": "Pedido movido e rotas recalculadas com sucesso!"}), 200

# --- ROTAS (ENTREGAS) ---

@api_bp.route('/api/routes', methods=['GET'])
def get_routes():
    """Busca todas as rotas."""
    try:
        routes = get_all_created_routes()
        return jsonify(routes), 200
    except Exception as e:
        return jsonify({"error": "Erro ao buscar rotas", "details": str(e)}), 500

@api_bp.route('/api/routes/<int:route_id>/assign', methods=['POST'])
def assign_route(route_id):
    """Atribui uma rota a um motoboy."""
    data = request.json
    motoboy_id = data.get('motoboy_id')
    
    if not motoboy_id:
        return jsonify({"error": "motoboy_id é obrigatório"}), 400

    if assign_route_to_motoboy(route_id, motoboy_id):
        return jsonify({"message": "Rota atribuída com sucesso!"}), 200
    else:
        return jsonify({"error": "Falha ao atribuir rota"}), 500

# --- MOTOBOYS ---

@api_bp.route('/api/motoboys', methods=['GET'])
def list_motoboys():
    """Lista todos os motoboys."""
    try:
        motoboys = get_all_motoboys()
        return jsonify(motoboys), 200
    except Exception as e:
        return jsonify({"error": "Erro ao listar motoboys", "details": str(e)}), 500

@api_bp.route('/api/motoboys', methods=['POST'])
def add_motoboy():
    """Cria um novo motoboy."""
    data = request.json
    name = data.get('name')
    # phone = data.get('phone') -> REMOVIDO
    
    if not name:
        return jsonify({"error": "Nome é obrigatório"}), 400
        
    # Chamamos a função sem passar o telefone
    if create_motoboy(name):
        return jsonify({"message": "Motoboy criado com sucesso"}), 201
    else:
        return jsonify({"error": "Erro ao criar motoboy"}), 500

@api_bp.route('/api/motoboys/<int:motoboy_id>/status', methods=['PUT'])
def change_motoboy_status(motoboy_id):
    """Altera o status do motoboy manualmente."""
    data = request.json
    status = data.get('status') # ex: 'available', 'unavailable'
    
    if not status:
        return jsonify({"error": "Status é obrigatório"}), 400
        
    if update_motoboy_status(motoboy_id, status):
        return jsonify({"message": "Status atualizado"}), 200
    else:
        return jsonify({"error": "Erro ao atualizar status"}), 500
    
@api_bp.route('/api/routes/<int:route_id>', methods=['PATCH'])
def update_route(route_id):
    """Atualiza dados da rota (Status)."""
    data = request.json
    status = data.get('status') # O front vai mandar: { "status": "completed" }
    
    if status:
        # Mapeamento do Front (ready, in_progress, completed) para o Banco
        # Se quiser manter simples, pode salvar igual, mas vamos garantir:
        if update_route_status_db(route_id, status):
            return jsonify({"message": "Status atualizado"}), 200
        else:
            return jsonify({"error": "Erro ao atualizar status"}), 500
            
    return jsonify({"message": "Nada a atualizar"}), 200

@api_bp.route('/api/routes/<int:route_id>/unassign', methods=['POST'])
def unassign_route(route_id):
    """Desatribui um motoboy de uma rota."""
    if unassign_route_from_motoboy(route_id):
        return jsonify({"message": "Rota desatribuída com sucesso!"}), 200
    else:
        return jsonify({"error": "Falha ao desatribuir rota"}), 500