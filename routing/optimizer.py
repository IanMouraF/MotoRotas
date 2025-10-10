import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcula a distância em quilômetros entre dois pontos de coordenadas
    usando a fórmula de Haversine.
    """
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def optimize_route(restaurant_coords, deliveries, deviation_tolerance=1.3):
    """
    Agrupa pedidos em rotas otimizadas baseadas em "corredores".

    Args:
        restaurant_coords (dict): Coordenadas do restaurante {'lat', 'lon'}.
        deliveries (list): Lista de todos os pedidos a serem entregues.
        deviation_tolerance (float): Fator de tolerância. Quanto maior, mais
                                     "torta" a rota pode ser. 1.3 significa que
                                     um desvio pode aumentar o percurso em até 30%.

    Returns:
        list: Uma lista de rotas. Cada rota é uma lista de pedidos ordenados.
    """
    if not deliveries:
        return []

    print("\n--- Iniciando otimização com algoritmo de corredor ---")
    
    # Adiciona a distância de cada entrega ao restaurante para uso futuro
    for d in deliveries:
        d['distance_from_restaurant'] = calculate_distance(
            restaurant_coords['lat'], restaurant_coords['lon'], d['lat'], d['lon']
        )

    all_routes = []
    unassigned_deliveries = list(deliveries)

    while unassigned_deliveries:
        # 1. Encontra o pedido mais distante para ser o "âncora" da nova rota
        anchor_delivery = max(unassigned_deliveries, key=lambda d: d['distance_from_restaurant'])
        current_route_candidates = [anchor_delivery]
        
        # Remove o âncora da lista de não atribuídos
        unassigned_deliveries.remove(anchor_delivery)
        
        deliveries_to_check = list(unassigned_deliveries) # Copia para iterar

        # Distância da rota direta: Restaurante -> Âncora
        direct_distance = anchor_delivery['distance_from_restaurant']

        # 2. Verifica quais outros pedidos se encaixam no "corredor"
        for candidate in deliveries_to_check:
            # Distância do desvio: Restaurante -> Candidato -> Âncora
            detour_distance = candidate['distance_from_restaurant'] + calculate_distance(
                candidate['lat'], candidate['lon'], anchor_delivery['lat'], anchor_delivery['lon']
            )

            # 3. Se o desvio for aceitável, adiciona à rota
            if detour_distance < direct_distance * deviation_tolerance:
                current_route_candidates.append(candidate)
                unassigned_deliveries.remove(candidate)
        
        # 4. Ordena a rota final pela distância do restaurante
        final_route = sorted(current_route_candidates, key=lambda d: d['distance_from_restaurant'])
        all_routes.append(final_route)

    print(f"--- Otimização finalizada: {len(all_routes)} rota(s) criada(s) ---")
    return all_routes

