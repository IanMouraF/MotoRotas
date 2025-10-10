from routing.optimizer import optimize_route
import urllib.parse

def create_google_maps_link(origin_coords, ordered_deliveries):
    """
    Cria um link do Google Maps com a rota otimizada a partir de coordenadas.
    """
    base_url = "https://www.google.com/maps/dir/"
    
    # Formata a string da origem
    origin_point = f"{origin_coords['lat']},{origin_coords['lon']}"
    
    # Formata a string das paradas
    delivery_points = [f"{d['lat']},{d['lon']}" for d in ordered_deliveries]
    
    # Junta todos os pontos em uma única string, separados por "/"
    full_path = "/".join([origin_point] + delivery_points)
    
    return base_url + full_path

def run_test():
    """
    Executa um teste do algoritmo de otimização com dados manuais.
    """

    # --- DADOS DE ENTRADA (VOCÊ PODE MUDAR AQUI) ---

    # Coordenadas do Restaurante (Ex: Bairro de Fátima, Fortaleza)
    restaurant_coords = {"lat": -3.7533, "lon": -38.5144}

    # Lista de entregas de exemplo com coordenadas em direções opostas
    
   #  {"id": "pedidoigreja", "lat": , "lon":  },
    sample_deliveries = [
        # Rota Sul
        { "id": "pedido_A_SUL_PERTO", "lat": -3.7658, "lon": -38.5120 }, # Perto (Aeroporto)
        { "id": "pedido_B_SUL_LONGE", "lat": -3.8345, "lon": -38.5029 }, # Longe (Messejana)

        # Rota Leste
        { "id": "pedido_C_LESTE_PERTO", "lat": -3.7448, "lon": -38.4900 }, # Perto (Cocó)
        { "id": "pedido_D_LESTE_LONGE", "lat": -3.7330, "lon": -38.4688 }, # Longe (Praia do Futuro)
        
        # Outro pedido na rota Leste para testar ordenação
        { "id": "pedido_E_LESTE_MEDIO", "lat": -3.7399, "lon": -38.4811 }, # Meio do caminho

        { "id": "pedido_TESTE", "lat": -3.796013, "lon": -38.505376 },
        {"id": "pedidoigreja", "lat": -3.796612939599661, "lon": -38.500149932026964 }, 

        {"id": "pedido_oeste_a", "lat": -3.7535693002164736, "lon": -38.53752621432585 },
       
        

        {"id": "pedido_norte_a", "lat": -3.7235924885333795, "lon": -38.51787098827868 },
         
    ]

    # --- EXECUÇÃO DO ALGORITMO ---
    
    print("="*50)
    print("INICIANDO TESTE DO ALGORITMO DE ROTA (CORREDORES)")
    print("="*50)
    
    # Chama a função de otimização
    list_of_routes = optimize_route(restaurant_coords, sample_deliveries)

    print("\n" + "="*50)
    print("RESULTADO FINAL: ROTAS GERADAS")
    print("="*50)

    if not list_of_routes:
        print("Nenhuma rota foi gerada.")
        return

    # Itera sobre cada rota criada e exibe as informações
    for i, route in enumerate(list_of_routes):
        print(f"\n--- ROTA {i + 1} ---")
        print("  Ordem de entrega:")
        for j, delivery in enumerate(route):
            print(f"    {j+1}º: Pedido {delivery['id']}")
        
        # Gera e exibe o link do Google Maps para esta rota específica
        maps_link = create_google_maps_link(restaurant_coords, route)
        print("\n  Link da Rota no Google Maps:")
        print(f"  {maps_link}")
    
    print("\n" + "="*50)


if __name__ == "__main__":
    run_test()

