import os
import sys
import uuid
import random

# Adiciona o diretório raiz do projeto ao sys.path para que possamos importar o manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import save_new_order

# Coordenadas do restaurante como base para a geração aleatória
RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

def generate_random_coords(base_coords, radius_km=5.0):
    """
    Gera coordenadas aleatórias dentro de um raio aproximado em km
    a partir de um ponto base.
    """
    # 1 grau de latitude é ~111km. 1km é ~0.009 graus.
    km_in_degrees = 0.009
    
    radius_in_degrees = radius_km * km_in_degrees
    
    random_lat = base_coords['lat'] + random.uniform(-radius_in_degrees, radius_in_degrees)
    random_lon = base_coords['lon'] + random.uniform(-radius_in_degrees, radius_in_degrees)
    
    return round(random_lat, 6), round(random_lon, 6)

def main():
    """Função principal para criar um pedido de teste."""
    print("--- Gerador de Pedidos de Teste ---")
    
    mode = input("Escolha o modo de criação: [a]leatório ou [m]anual? (a/m): ").lower()
    
    lat, lon = 0.0, 0.0
    
    if mode == 'm':
        try:
            lat_str = input("Digite a latitude (ex: -3.78): ")
            lon_str = input("Digite a longitude (ex: -38.50): ")
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            print("❌ Erro: Latitude e longitude devem ser números. Operação cancelada.")
            return
            
    elif mode == 'a':
        radius_km_str = input("Digite o raio máximo em km a partir do restaurante (padrão: 5km): ")
        if not radius_km_str:
            radius_km = 5.0
        else:
            try:
                radius_km = float(radius_km_str)
            except ValueError:
                print("❌ Erro: O raio deve ser um número. Usando o padrão de 5km.")
                radius_km = 5.0

        lat, lon = generate_random_coords(RESTAURANT_COORDS, radius_km)
        print(f"   -> Coordenadas geradas: Latitude={lat}, Longitude={lon}")
        
    else:
        print("Opção inválida. Operação cancelada.")
        return
        
    # Cria o objeto do pedido com um ID único
    new_order_data = {
        'id': str(uuid.uuid4()),
        'lat': lat,
        'lon': lon
    }
    
    # Salva o novo pedido no banco de dados
    print("\nSalvando novo pedido no banco de dados...")
    save_new_order(new_order_data)

if __name__ == "__main__":
    main()
    