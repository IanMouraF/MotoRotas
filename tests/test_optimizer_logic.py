import pytest
from app.routing.optimizer import calculate_distance, reorder_route

def test_calculate_distance_accuracy():
    """Testa se o cálculo de distância está preciso (margem de erro pequena)."""
    # Distância aproximada entre dois pontos conhecidos em Fortaleza
    p1 = {"lat": -3.783871, "lon": -38.500820}
    p2 = {"lat": -3.784871, "lon": -38.500820} # Aprox 111 metros ao sul
    
    dist = calculate_distance(p1, p2)
    # 0.111 km = 111 metros. Aceitamos uma margem de erro de 0.01
    assert dist == pytest.approx(0.111, abs=0.01)

def test_reorder_route_simple():
    """Verifica se ele reordena pelo vizinho mais próximo corretamente."""
    restaurant = {"lat": 0, "lon": 0}
    
    # Cria 3 pedidos: Perto (1,1), Médio (5,5) e Longe (10,10)
    # Mas entrega a lista BAGUNÇADA para a função
    orders = [
        {"id": "longe", "coords": {"lat": 10, "lon": 10}},
        {"id": "perto", "coords": {"lat": 1, "lon": 1}},
        {"id": "medio", "coords": {"lat": 5, "lon": 5}},
    ]
    
    ordered = reorder_route(orders, restaurant)
    
    # A ordem correta deve ser: Perto -> Médio -> Longe
    assert ordered[0]['id'] == 'perto'
    assert ordered[1]['id'] == 'medio'
    assert ordered[2]['id'] == 'longe'