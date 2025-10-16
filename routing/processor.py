# Este arquivo é o nosso antigo process_routes.py, refatorado para ser um módulo.

import os
import sys
import time

# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import get_pending_orders, get_created_routes, create_new_route, update_route
from routing.optimizer import find_best_route_for_order, reorder_route, create_google_maps_link

RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

def processor_cycle():
    """Executa um único ciclo de processamento de rotas."""
    pending_orders = get_pending_orders()

    if not pending_orders:
        return # Continua silenciosamente

    print(f"✅ Processador: {len(pending_orders)} pedido(s) pendente(s) encontrado(s). Otimizando...")
    existing_routes = get_created_routes()
    
    for order in pending_orders:
        best_route = find_best_route_for_order(order, existing_routes, RESTAURANT_COORDS)
        
        if best_route:
            best_route['orders'].append(order)
            best_route['orders'] = reorder_route(best_route['orders'], RESTAURANT_COORDS)
            best_route['google_maps_link'] = create_google_maps_link(RESTAURANT_COORDS, best_route['orders'])
            update_route(best_route)
        else:
            new_route_id = create_new_route(order, RESTAURANT_COORDS)
            existing_routes.append({'id': new_route_id, 'orders': [order]})
            
    print("   -> Ciclo de processamento concluído.")

def start_processor_loop():
    """Inicia o loop infinito do processador de rotas."""
    interval = 3
    print(f"--- PROCESSADOR DE ROTAS INICIADO (verificando a cada {interval}s) ---")
    while True:
        try:
            processor_cycle()
            time.sleep(interval)
        except Exception as e:
            print(f"\n🚨 Processador: Erro inesperado no loop: {e}")
            time.sleep(interval)
