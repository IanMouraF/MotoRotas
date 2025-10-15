import os
import sys
import time

# Adiciona o diretório raiz ao sys.path para resolver importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.manager import get_pending_orders, get_created_routes, create_new_route, update_route
from routing.optimizer import find_best_route_for_order, reorder_route, create_google_maps_link

# Coordenadas do restaurante (precisa ser consistente com outros scripts)
RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

def main_loop():
    """Função principal que executa um ciclo de processamento de rotas."""
    pending_orders = get_pending_orders()

    if not pending_orders:
        # Nenhum pedido pendente, o loop continua silenciosamente
        return

    print(f"✅ Processador: {len(pending_orders)} pedido(s) pendente(s) encontrados. Otimizando...")

    # Busca as rotas que já existem e estão em aberto
    existing_routes = get_created_routes()
    
    # Processa um pedido de cada vez, aplicando a lógica incremental
    for order in pending_orders:
        print(f"   -> Processando Pedido ID: {order['id'][:8]}...")
        best_route = find_best_route_for_order(order, existing_routes, RESTAURANT_COORDS)
        
        if best_route:
            print(f"      Decisão: Adicionando à Rota existente #{best_route['id']}")
            best_route['orders'].append(order)
            best_route['orders'] = reorder_route(best_route['orders'], RESTAURANT_COORDS)
            best_route['google_maps_link'] = create_google_maps_link(RESTAURANT_COORDS, best_route['orders'])
            update_route(best_route)
        else:
            print(f"      Decisão: Criando nova Rota.")
            new_route_id = create_new_route(order, RESTAURANT_COORDS)
            # Adiciona a nova rota à lista para que possa ser considerada pelos próximos pedidos no mesmo ciclo
            existing_routes.append({
                'id': new_route_id, 
                'orders': [order],
                'google_maps_link': ''
            })
            
    print("   -> Ciclo de processamento concluído.")


if __name__ == "__main__":
    PROCESSING_INTERVAL_SECONDS = 3
    print("--- INICIANDO PROCESSADOR DE ROTAS (Pressione Ctrl+C para parar) ---")
    while True:
        try:
            main_loop()
            time.sleep(PROCESSING_INTERVAL_SECONDS)
        except Exception as e:
            print(f"\n🚨 Processador: Ocorreu um erro inesperado no loop: {e}")
            print(f"--- Tentando novamente em {PROCESSING_INTERVAL_SECONDS} segundos ---")
            time.sleep(PROCESSING_INTERVAL_SECONDS)

