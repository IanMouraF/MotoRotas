import math
import urllib.parse
import numpy as np

# --- PARÂMETROS DE CONFIGURAÇÃO DO ALGORITMO ---
# Ajuste estes valores para tornar o algoritmo mais ou menos rigoroso.

# Largura máxima (em km) do "corredor" da rota. Pontos não podem estar mais longe que isso da linha reta.
# Um valor menor cria rotas mais "retas".
CORRIDOR_WIDTH_KM = 0.8

# Desvio máximo (em km) permitido. A soma da distância (restaurante -> ponto) + (ponto -> âncora)
# não pode exceder a distância (restaurante -> âncora) por mais que este valor.
MAX_DETOUR_KM = 1.5


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

def is_candidate_for_route(restaurant_coords, route_orders, new_order_coords, corridor_width, max_detour):
    """Verifica se um novo pedido é um candidato viável para se juntar a uma rota existente."""
    if not route_orders:
        return False

    # Cenário 1: O novo pedido se encaixa no corredor da rota existente.
    current_anchor = max(route_orders, key=lambda p: calculate_distance(restaurant_coords, p['coords']))
    if _is_on_the_way(restaurant_coords, current_anchor['coords'], new_order_coords, corridor_width, max_detour):
        return True

    # Cenário 2: A rota existente inteira se encaixa no corredor do novo pedido (se ele for mais distante).
    new_order_dist = calculate_distance(restaurant_coords, new_order_coords)
    if new_order_dist > calculate_distance(restaurant_coords, current_anchor['coords']):
        all_orders_fit = all(
            _is_on_the_way(restaurant_coords, new_order_coords, existing_order['coords'], corridor_width, max_detour)
            for existing_order in route_orders
        )
        if all_orders_fit:
            return True
    
    return False

def _is_on_the_way(restaurant_coords, anchor_coords, check_coords, corridor_width, max_detour):
    """Função auxiliar para verificar se um ponto está no 'corredor' de outro."""
    # Verificação vetorial de direção
    vec_anchor_x = anchor_coords['lon'] - restaurant_coords['lon']
    vec_anchor_y = anchor_coords['lat'] - restaurant_coords['lat']
    vec_check_x = check_coords['lon'] - restaurant_coords['lon']
    vec_check_y = check_coords['lat'] - restaurant_coords['lat']
    
    dot_product = (vec_anchor_x * vec_check_x) + (vec_anchor_y * vec_check_y)
    if dot_product <= 0:
        return False

    # Verificações de distância e desvio
    dist_rest_check = calculate_distance(restaurant_coords, check_coords)
    dist_anchor_check = calculate_distance(anchor_coords, check_coords)
    dist_rest_anchor = calculate_distance(restaurant_coords, anchor_coords)
    
    if dist_rest_check > dist_rest_anchor + 0.1: # Pequena tolerância
        return False
    if dist_rest_check + dist_anchor_check > dist_rest_anchor + max_detour:
        return False

    return True


# --- FUNÇÃO PARA CRIAR LINK DE NAVEGAÇÃO ---

def create_google_maps_link(origin_coords, ordered_deliveries):
    """Cria um link do Google Maps com uma rota de múltiplos destinos."""
    base_url = "https://www.google.com/maps/dir/"
    origin_point = f"{origin_coords['lat']},{origin_coords['lon']}"
    delivery_points = [f"{p['coords']['lat']},{p['coords']['lon']}" for p in ordered_deliveries]
    all_points = [origin_point] + delivery_points
    url_final = base_url + "/".join(all_points)
    url_final += "?travelmode=driving"
    return url_final

# --- NOVAS FUNÇÕES DO ALGORITMO INCREMENTAL ---

def get_route_total_distance(orders, restaurant_coords):
    """Calcula a distância total de uma rota, seguindo a ordem dos pedidos."""
    if not orders:
        return 0
    
    total_distance = 0
    current_location = restaurant_coords
    for order in orders:
        total_distance += calculate_distance(current_location, order['coords'])
        current_location = order['coords']
    return total_distance

def reorder_route(orders, restaurant_coords):
    """Reordena os pedidos de uma rota usando a heurística do 'vizinho mais próximo'."""
    if not orders:
        return []

    remaining_orders = list(orders)
    ordered_route = []
    current_location = restaurant_coords
    
    while remaining_orders:
        closest_order = min(remaining_orders, key=lambda order: calculate_distance(current_location, order['coords']))
        ordered_route.append(closest_order)
        remaining_orders.remove(closest_order)
        current_location = closest_order['coords']
        
    return ordered_route

def calculate_direction_penalty(route_orders, new_order, restaurant_coords):
    """Calcula uma penalidade baseada na consistência direcional."""
    if len(route_orders) < 1:
        return 0 # Nenhuma penalidade se a rota tiver apenas um pedido ou estiver vazia
    
    # Vetor médio da rota existente
    avg_vec_x, avg_vec_y = 0, 0
    for order in route_orders:
        avg_vec_x += order['coords']['lon'] - restaurant_coords['lon']
        avg_vec_y += order['coords']['lat'] - restaurant_coords['lat']
    
    # Vetor do novo pedido
    new_vec_x = new_order['coords']['lon'] - restaurant_coords['lon']
    new_vec_y = new_order['coords']['lat'] - restaurant_coords['lat']

    # Normaliza os vetores
    norm_avg = np.sqrt(avg_vec_x**2 + avg_vec_y**2)
    norm_new = np.sqrt(new_vec_x**2 + new_vec_y**2)
    
    if norm_avg == 0 or norm_new == 0:
        return 0

    avg_vec_x /= norm_avg
    avg_vec_y /= norm_avg
    new_vec_x /= norm_new
    new_vec_y /= norm_new
    
    # Produto escalar entre os vetores normalizados (cosseno do ângulo)
    dot_product = (avg_vec_x * new_vec_x) + (avg_vec_y * new_vec_y)
    
    # A penalidade é maior quando o cosseno é menor (ângulo maior)
    # (1 - cosseno) varia de 0 (mesma direção) a 2 (direção oposta)
    penalty = (1 - dot_product)
    
    # Amplifica a penalidade para torná-la mais significativa em comparação com a distância
    return penalty * 5 


def find_best_route_for_order(new_order, existing_routes, restaurant_coords):
    """
    Avalia um novo pedido contra todas as rotas existentes e encontra a melhor opção
    baseada no menor custo (distância + penalidade direcional).
    """
    best_fit_route = None
    min_cost = float('inf')

    for route in existing_routes:
        if not is_candidate_for_route(restaurant_coords, route['orders'], new_order['coords'], CORRIDOR_WIDTH_KM, MAX_DETOUR_KM):
            continue

        # Calcula o custo de adicionar o novo pedido
        original_ordered_route = reorder_route(route['orders'], restaurant_coords)
        original_distance = get_route_total_distance(original_ordered_route, restaurant_coords)

        potential_new_route_orders = route['orders'] + [new_order]
        new_ordered_route = reorder_route(potential_new_route_orders, restaurant_coords)
        new_distance = get_route_total_distance(new_ordered_route, restaurant_coords)
        
        added_distance = new_distance - original_distance
        
        # Calcula a penalidade direcional
        penalty = calculate_direction_penalty(route['orders'], new_order, restaurant_coords)
        
        # O custo total é a distância adicionada mais a penalidade
        total_cost = added_distance + penalty

        if total_cost < min_cost:
            min_cost = total_cost
            best_fit_route = route

    if best_fit_route and min_cost < (MAX_DETOUR_KM + 5): # Limiar de custo ajustado para incluir a penalidade
        return best_fit_route
    
    return None

