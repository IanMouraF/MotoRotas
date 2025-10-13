import math
import urllib.parse

# --- FUNÇÕES DE CÁLCULO GEOGRÁFICO ---

def calculate_distance(point1, point2):
    """Calcula a distância em km entre duas coordenadas geográficas (lat, lon)."""
    R = 6371  # Raio da Terra em km
    lat1, lon1 = math.radians(point1['lat']), math.radians(point1['lon'])
    lat2, lon2 = math.radians(point2['lat']), math.radians(point2['lon'])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

def is_on_the_way(restaurant_coords, anchor_coords, check_coords, corridor_width_km, max_detour_km):
    """Verifica se um ponto está no 'corredor' entre o restaurante e o ponto âncora."""
    dist_rest_anchor = calculate_distance(restaurant_coords, anchor_coords)
    dist_rest_check = calculate_distance(restaurant_coords, check_coords)
    dist_anchor_check = calculate_distance(anchor_coords, check_coords)

    if dist_rest_check > dist_rest_anchor + max_detour_km:
        return False

    if dist_rest_check + dist_anchor_check > dist_rest_anchor + corridor_width_km:
        return False

    return True

# --- FUNÇÃO PARA CRIAR LINK DE NAVEGAÇÃO ---

def create_google_maps_link(origin_coords, ordered_deliveries):
    """Cria um link do Google Maps com uma rota de múltiplos destinos."""
    base_url = "https://www.google.com/maps/dir/"
    
    all_points = [f"{origin_coords['lat']},{origin_coords['lon']}"]
    for delivery in ordered_deliveries:
        coords = delivery['coords']
        all_points.append(f"{coords['lat']},{coords['lon']}")

    url_final = base_url + "/".join(all_points)
    return url_final

# --- NOVAS FUNÇÕES DO ALGORITMO INCREMENTAL ---

def reorder_route(orders, restaurant_coords):
    """Reordena os pedidos de uma rota pela distância do restaurante."""
    return sorted(orders, key=lambda p: calculate_distance(restaurant_coords, p['coords']))

def find_best_route_for_order(new_order, existing_routes, restaurant_coords, corridor_width_km=2.0, max_detour_km=4.0):
    """
    Avalia um novo pedido contra rotas existentes e encontra a melhor para encaixá-lo.
    
    Args:
        new_order (dict): O novo pedido a ser avaliado.
        existing_routes (list): Uma lista de rotas já criadas.
        restaurant_coords (dict): Coordenadas do restaurante.
    
    Returns:
        A rota (dict) na qual o pedido se encaixa, ou None se não encontrar nenhuma.
    """
    best_fit_route = None
    
    for route in existing_routes:
        if not route['orders']:
            continue
            
        # Cenário 1: O novo pedido se encaixa no corredor da rota existente.
        current_anchor = max(route['orders'], key=lambda p: calculate_distance(restaurant_coords, p['coords']))
        if is_on_the_way(
            restaurant_coords, 
            current_anchor['coords'], 
            new_order['coords'], 
            corridor_width_km, 
            max_detour_km
        ):
            best_fit_route = route
            break

        # Cenário 2: A rota existente inteira se encaixa no corredor do novo pedido (se ele for mais distante).
        new_order_dist = calculate_distance(restaurant_coords, new_order['coords'])
        if new_order_dist > calculate_distance(restaurant_coords, current_anchor['coords']):
            # Verifica se TODOS os pedidos existentes na rota estão a caminho do novo pedido.
            all_orders_fit = all(
                is_on_the_way(
                    restaurant_coords, 
                    new_order['coords'], 
                    existing_order['coords'], 
                    corridor_width_km, 
                    max_detour_km
                ) for existing_order in route['orders']
            )
            
            if all_orders_fit:
                best_fit_route = route
                break
            
    return best_fit_route

