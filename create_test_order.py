import os
import sys
import uuid
import random
import math

# Adiciona o diretório raiz do projeto ao sys.path para que possamos importar o manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import save_new_order

# Coordenadas do restaurante como base para a geração aleatória
RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

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

def generate_random_coords(base_coords, radius_km=5.0):
    """
    Gera coordenadas aleatórias GARANTIDAMENTE dentro de um raio em km
    a partir de um ponto base, usando rejection sampling.
    """
    # 1 grau de latitude é ~111km. 1km é ~0.009 graus.
    km_in_degrees = 0.009
    
    # Gera pontos em um quadrado ao redor do ponto base
    radius_in_degrees = radius_km * km_in_degrees
    
    while True:
        random_lat = base_coords['lat'] + random.uniform(-radius_in_degrees, radius_in_degrees)
        random_lon = base_coords['lon'] + random.uniform(-radius_in_degrees, radius_in_degrees)
        
        new_point = {"lat": random_lat, "lon": random_lon}
        
        # Verifica se o ponto gerado está dentro do raio circular
        if calculate_distance(base_coords, new_point) <= radius_km:
            return round(random_lat, 6), round(random_lon, 6)

def create_single_manual_order():
    """Cria um único pedido com coordenadas manuais."""
    try:
        lat_str = input("Digite a latitude (ex: -3.78): ")
        lon_str = input("Digite a longitude (ex: -38.50): ")
        lat = float(lat_str)
        lon = float(lon_str)
        
        new_order_data = {'id': str(uuid.uuid4()), 'lat': lat, 'lon': lon}
        print("\nSalvando novo pedido no banco de dados...")
        save_new_order(new_order_data)

    except ValueError:
        print("❌ Erro: Latitude e longitude devem ser números. Operação cancelada.")
        return

def create_random_orders(count=1):
    """Cria uma quantidade definida de pedidos com coordenadas aleatórias."""
    radius_km_str = input(f"Digite o raio máximo em km a partir do restaurante (padrão: 5km): ")
    if not radius_km_str:
        radius_km = 5.0
    else:
        try:
            radius_km = float(radius_km_str)
        except ValueError:
            print("❌ Erro: O raio deve ser um número. Usando o padrão de 5km.")
            radius_km = 5.0
    
    print(f"\nCriando {count} pedido(s) aleatório(s)...")
    for i in range(count):
        lat, lon = generate_random_coords(RESTAURANT_COORDS, radius_km)
        print(f"   -> Pedido {i+1}/{count} gerado com coordenadas: Lat={lat}, Lon={lon}")
        new_order_data = {'id': str(uuid.uuid4()), 'lat': lat, 'lon': lon}
        save_new_order(new_order_data)
    
    print(f"\n✅ {count} pedido(s) criado(s) com sucesso!")


def main():
    """Função principal para criar um pedido de teste."""
    print("--- Gerador de Pedidos de Teste ---")
    
    mode = input("Escolha o modo: [a]leatório (1), [m]anual (1) ou [v]ários aleatórios? (a/m/v): ").lower()
    
    if mode == 'm':
        create_single_manual_order()
            
    elif mode == 'a':
        create_random_orders(count=1)
        
    elif mode == 'v':
        try:
            num_orders_str = input("Quantos pedidos aleatórios deseja criar? ")
            num_orders = int(num_orders_str)
            if num_orders > 0:
                create_random_orders(count=num_orders)
            else:
                print("O número de pedidos deve ser maior que zero.")
        except ValueError:
            print("❌ Erro: Por favor, digite um número válido. Operação cancelada.")
            return

    else:
        print("Opção inválida. Operação cancelada.")
        return

if __name__ == "__main__":
    main()

