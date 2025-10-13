import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path para resolver os imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routing.optimizer import find_best_route_for_order, reorder_route, create_google_maps_link

# --- CONFIGURAÇÕES ---
RESTAURANT_COORDS = {"lat": -3.783871, "lon": -38.500820}

# --- DADOS DE ENTRADA (SIMULAÇÃO DE PEDIDOS CHEGANDO UM A UM) ---
INCOMING_ORDERS = [
    # Rota Sul
    {"id": "Pedido_A_Sul", "coords": {"lat": -3.805, "lon": -38.505}},
    {"id": "Pedido_B_Sul_Distante", "coords": {"lat": -3.830, "lon": -38.510}},
    
    # Rota Norte
    {"id": "Pedido_C_Norte", "coords": {"lat": -3.760, "lon": -38.495}},
    
    # Pedido Sul que se encaixa na primeira rota
    {"id": "Pedido_D_Sul_Intermediario", "coords": {"lat": -3.815, "lon": -38.508}},
    
    # Pedido muito a Leste, que não deve se encaixar em nenhuma
    {"id": "Pedido_E_Leste_Isolado", "coords": {"lat": -3.790, "lon": -38.460}},
]

# --- SIMULAÇÃO DO PROCESSO ---
if __name__ == "__main__":
    
    # Começamos sem nenhuma rota criada
    final_routes = []

    print("--- Iniciando Simulação de Recebimento de Pedidos ---\n")

    # Processa cada pedido que "chega"
    for new_order in INCOMING_ORDERS:
        print(f"-> Chegou um novo pedido: {new_order['id']}")
        
        # O algoritmo tenta encontrar uma rota existente para o novo pedido
        best_route_found = find_best_route_for_order(
            new_order, final_routes, RESTAURANT_COORDS
        )
        
        if best_route_found:
            # Se encontrou uma rota, adiciona o pedido a ela
            print(f"   Decisão: Adicionando à Rota existente #{best_route_found['id']}\n")
            best_route_found['orders'].append(new_order)
            # Reordena a rota com o novo pedido
            best_route_found['orders'] = reorder_route(best_route_found['orders'], RESTAURANT_COORDS)
        else:
            # Se não encontrou, cria uma nova rota
            new_route_id = len(final_routes) + 1
            print(f"   Decisão: Nenhuma rota compatível. Criando nova Rota #{new_route_id}\n")
            final_routes.append({
                "id": new_route_id,
                "orders": [new_order]
            })

    # --- EXIBIÇÃO DO RESULTADO FINAL ---
    print("\n--- Resultado Final da Otimização ---")
    
    if not final_routes:
        print("Nenhuma rota foi criada.")
    else:
        for route in final_routes:
            # Recalcula o link do Google Maps com a composição final
            gmaps_link = create_google_maps_link(RESTAURANT_COORDS, route['orders'])
            
            print(f"\n-> Rota #{route['id']}")
            print("   Pedidos (em ordem de entrega):")
            for order in route['orders']:
                print(f"     - {order['id']}")
            print(f"   Link de Navegação: {gmaps_link}")

