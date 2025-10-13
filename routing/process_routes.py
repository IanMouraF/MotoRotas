import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path para resolver os imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.manager import get_pending_orders, get_created_routes, update_route, create_new_route
from routing.optimizer import find_best_route_for_order, reorder_route, create_google_maps_link

# --- CONFIGURAÇÕES ---
RESTAURANT_COORDS = {"lat": -3.783871, "lon": -38.500820}

if __name__ == "__main__":
    print("Iniciando processamento incremental de rotas...")

    # 1. Busca os dados do banco de dados
    pending_orders = get_pending_orders()
    existing_routes = get_created_routes() # Busca rotas que ainda não foram atribuídas

    if not pending_orders:
        print("✅ Nenhum pedido pendente para processar.")
        sys.exit()

    print(f"Encontrado(s) {len(pending_orders)} pedido(s) pendente(s) e {len(existing_routes)} rota(s) existente(s).")

    # 2. Processa cada pedido pendente, um por um
    for order in pending_orders:
        print(f"\n-> Processando Pedido ID: {order['id']}")
        
        best_route_found = find_best_route_for_order(order, existing_routes, RESTAURANT_COORDS)

        if best_route_found:
            # Se encontrou uma rota, adiciona o pedido a ela
            print(f"   Decisão: Adicionando à Rota existente #{best_route_found['id']}")
            best_route_found['orders'].append(order)
            best_route_found['orders'] = reorder_route(best_route_found['orders'], RESTAURANT_COORDS)
            
            # Atualiza o link do Google Maps e salva no banco de dados
            new_link = create_google_maps_link(RESTAURANT_COORDS, best_route_found['orders'])
            best_route_found['google_maps_link'] = new_link
            update_route(best_route_found)

        else:
            # Se não encontrou, cria uma nova rota
            new_route_id = create_new_route(order, RESTAURANT_COORDS)
            print(f"   Decisão: Nenhuma rota compatível. Criando nova Rota #{new_route_id}")
            
            # Adiciona a nova rota à lista de rotas existentes para a próxima iteração
            new_route_in_memory = {
                'id': new_route_id,
                'orders': [order],
                'status': 'created',
                'google_maps_link': create_google_maps_link(RESTAURANT_COORDS, [order])
            }
            existing_routes.append(new_route_in_memory)
            
    print("\n✅ Processamento incremental de rotas concluído.")

