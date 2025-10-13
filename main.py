import os
import requests
from dotenv import load_dotenv
import urllib.parse

# Importa nosso algoritmo de otimização
from routing.optimizer import optimize_route

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURAÇÕES ---
# Pegas as credenciais do arquivo .env
CLIENT_ID = os.getenv("IFOOD_CLIENT_ID")
CLIENT_SECRET = os.getenv("IFOOD_CLIENT_SECRET")

# URLs da API de Sandbox do iFood
AUTH_API_URL = "https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token"
ORDER_API_URL = "https://merchant-api.ifood.com.br/order/v1.0"

# !!! IMPORTANTE: COLOQUE AS COORDENADAS DO SEU RESTAURANTE AQUI !!!
# Este é o ponto de partida para todas as rotas.
RESTAURANT_COORDS = {"lat": -3.783871639912979, "lon": -38.50082092785248}

# --- FUNÇÕES AUXILIARES ---

def create_google_maps_link(origin_coords, ordered_deliveries):
    """
    Cria um link do Google Maps com a rota otimizada a partir de coordenadas.
    """
    base_url = "https://www.google.com/maps/dir/"
    origin_point = f"{origin_coords['lat']},{origin_coords['lon']}"
    delivery_points = [f"{d['lat']},{d['lon']}" for d in ordered_deliveries]
    full_path = "/".join([origin_point] + delivery_points)
    return base_url + full_path

def authenticate():
    """Autentica na API e retorna o token de acesso."""
    print("1. Tentando autenticar na API do iFood...")
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grantType': 'client_credentials',
        'clientId': CLIENT_ID,
        'clientSecret': CLIENT_SECRET
    }
    response = requests.post(AUTH_API_URL, headers=headers, data=data)

    if response.status_code == 200:
        print("✅ Autenticação bem-sucedida!")
        return response.json()['accessToken']
    else:
        print(f"❌ Falha na autenticação! Código: {response.status_code}")
        print("Resposta:", response.text)
        return None

def get_new_orders(token):
    """Busca por novos eventos (pedidos) na API."""
    print("\n2. Buscando por novos pedidos...")
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{ORDER_API_URL}/events:polling", headers=headers)

    if response.status_code == 204:
        print("✅ Nenhum pedido novo encontrado.")
        return []
    elif response.status_code == 200:
        events = response.json()
        print(f"✅ Encontrado(s) {len(events)} novo(s) evento(s)!")
        return events
    else:
        print(f"❌ Erro ao buscar pedidos! Código: {response.status_code}")
        print("Resposta:", response.text)
        return []

def get_order_details(token, order_id):
    """Busca os detalhes de um pedido específico."""
    print(f"   - Buscando detalhes do pedido {order_id}...")
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{ORDER_API_URL}/orders/{order_id}", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"   - ❌ Erro ao buscar detalhes do pedido {order_id}! Código: {response.status_code}")
        return None

def acknowledge_orders(token, events):
    """Confirma o recebimento dos eventos para a API do iFood."""
    print("\n5. Confirmando recebimento dos eventos...")
    headers = {'Authorization': f'Bearer {token}'}
    data = [{'id': event['id']} for event in events]
    response = requests.post(f"{ORDER_API_URL}/events/acknowledgment", headers=headers, json=data)

    if response.status_code == 202:
        print("✅ Eventos confirmados com sucesso!")
    else:
        print(f"❌ Falha ao confirmar eventos! Código: {response.status_code}")
        print("Resposta:", response.text)

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    access_token = authenticate()

    if access_token:
        events = get_new_orders(access_token)
        
        if events:
            deliveries_to_process = []
            
            print("\n3. Coletando informações dos pedidos...")
            for event in events:
                if event.get('code') == 'PLC': # PLC = Pedido realizado
                    order_id = event.get('orderId')
                    details = get_order_details(access_token, order_id)
                    if details and details.get('delivery', {}).get('deliveryAddress'):
                        address = details['delivery']['deliveryAddress']
                        coordinates = address.get('coordinates', {})
                        
                        # Adiciona o pedido na lista para otimização
                        deliveries_to_process.append({
                            "id": order_id,
                            "lat": coordinates.get('latitude', 0.0),
                            "lon": coordinates.get('longitude', 0.0)
                        })

            if deliveries_to_process:
                print("\n4. Otimizando rotas com os pedidos encontrados...")
                # Chama nosso algoritmo para criar as rotas
                list_of_routes = optimize_route(RESTAURANT_COORDS, deliveries_to_process)

                print("\n" + "="*50)
                print("ROTAS GERADAS")
                print("="*50)

                for i, route in enumerate(list_of_routes):
                    print(f"\n--- ROTA {i + 1} ---")
                    print("  Ordem de entrega:")
                    for j, delivery in enumerate(route):
                        print(f"    {j+1}º: Pedido ID {delivery['id']}")
                    
                    maps_link = create_google_maps_link(RESTAURANT_COORDS, route)
                    print("\n  Link da Rota no Google Maps:")
                    print(f"  {maps_link}")
                print("\n" + "="*50)
            
            # Confirma os eventos para o iFood
            acknowledge_orders(access_token, events)


