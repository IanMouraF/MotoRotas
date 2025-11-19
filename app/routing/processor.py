import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.manager import get_pending_orders, get_created_routes, create_new_route, update_route
from app.routing.optimizer import find_best_route_for_order, reorder_route, create_google_maps_link

RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

def processor_cycle():
    """Executa um único ciclo de processamento de rotas."""
    pending_orders = get_pending_orders()

    if not pending_orders:
        return

    print(f"✅ Processador: {len(pending_orders)} pedido(s) pendente(s) encontrado(s). Otimizando...")
    existing_routes = get_created_routes()
    
    for order in pending_orders:
        best_route = find_best_route_for_order(order, existing_routes, RESTAURANT_COORDS)
        
        if best_route:
            # CASO 1: Adiciona a uma rota existente
            best_route['orders'].append(order)
            best_route['orders'] = reorder_route(best_route['orders'], RESTAURANT_COORDS)
            best_route['google_maps_link'] = create_google_maps_link(RESTAURANT_COORDS, best_route['orders'])
            update_route(best_route)
        else:
            # CASO 2: Cria uma nova rota
            new_route_id = create_new_route(order, RESTAURANT_COORDS)
            new_route_orders = [order]
            link = create_google_maps_link(RESTAURANT_COORDS, new_route_orders)
            
            new_route_data = {
                'id': new_route_id,
                'orders': new_route_orders,
                'google_maps_link': link
            }
            update_route(new_route_data)


            existing_routes.append(new_route_data)
            
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