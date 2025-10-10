import os
import requests
from dotenv import load_dotenv
from routing.optimizer import optimize_route # <-- IMPORTA NOSSA NOVA FUNÇÃO

load_dotenv()

# --- Configurações ---
CLIENT_ID = os.getenv("IFOOD_CLIENT_ID")
CLIENT_SECRET = os.getenv("IFOOD_CLIENT_SECRET")
BASE_API_URL = "https://merchant-api.ifood.com.br"

# Coordenadas fixas do restaurante (exemplo)
# No futuro, podemos buscar isso da API ou configurar em outro lugar
RESTAURANT_COORDS = {"lat": -3.7427, "lon": -38.5023} # Exemplo: Ponto em Fortaleza

def authenticate():
    """Busca o token de acesso na API do iFood."""
    print("1. Tentando autenticar na API do iFood...")
    url = f"{BASE_API_URL}/authentication/v1.0/oauth/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        "grantType": "client_credentials",
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET
    }
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        print("✅ Autenticação bem-sucedida!")
        return response.json()['accessToken']
    else:
        print("❌ Falha na autenticação!")
        print(f"Status: {response.status_code}, Resposta: {response.text}")
        return None

def get_new_orders(token):
    """Busca por novos eventos (pedidos) na API."""
    print("\n2. Buscando por novos pedidos...")
    url = f"{BASE_API_URL}/order/v1.0/events:polling"
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        events = response.json()
        if events:
            print(f"✅ Encontrado(s) {len(events)} novo(s) evento(s)!")
            return events
        else:
            # A API pode retornar 200 com corpo vazio se não houver eventos
            print("🔵 Nenhum pedido novo encontrado.")
            return []
    elif response.status_code == 204: # No Content
        print("🔵 Nenhum pedido novo encontrado.")
        return []
    else:
        print("❌ Ocorreu um erro ao buscar pedidos!")
        print(f"Status: {response.status_code}, Resposta: {response.text}")
        return []

def get_order_details(token, order_id):
    """Busca os detalhes de um pedido específico."""
    print(f"   - Buscando detalhes do pedido {order_id}...")
    url = f"{BASE_API_URL}/order/v1.0/orders/{order_id}"
    headers = {'Authorization': f'Bearer {token}'}

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"   - ❌ Falha ao buscar detalhes do pedido {order_id}")
        return None

def acknowledge_orders(token, events):
    """Confirma o recebimento dos eventos para a API."""
    if not events:
        return
        
    print("\n4. Confirmando recebimento dos eventos...")
    url = f"{BASE_API_URL}/order/v1.0/events/acknowledgment"
    headers = {'Authorization': f'Bearer {token}'}
    data = [{"id": event['id']} for event in events]

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 202:
        print("✅ Eventos confirmados com sucesso!")
    else:
        print("❌ Falha ao confirmar eventos!")
        print(f"Status: {response.status_code}, Resposta: {response.text}")

def main():
    """Função principal que orquestra as chamadas."""
    access_token = authenticate()
    if not access_token:
        return

    events = get_new_orders(access_token)
    if not events:
        return

    # Lista para armazenar os detalhes dos pedidos para o algoritmo
    deliveries_to_optimize = []

    print("\n3. Processando detalhes dos pedidos...")
    for event in events:
        if event.get('code') == 'PLC': # PLC = Placed (Pedido feito)
            order_id = event.get('orderId')
            if order_id:
                details = get_order_details(access_token, order_id)
                if details and details.get('delivery'):
                    address = details['delivery']['deliveryAddress']
                    coordinates = address.get('coordinates', {})
                    lat = coordinates.get('latitude')
                    lon = coordinates.get('longitude')
                    
                    if lat is not None and lon is not None:
                        # Adiciona o pedido na lista para otimização
                        deliveries_to_optimize.append({
                            "id": order_id,
                            "lat": lat,
                            "lon": lon
                        })
                    else:
                        print(f"   - ⚠️ Pedido {order_id} sem coordenadas.")
    
    # Se encontramos pedidos com coordenadas, chamamos o algoritmo
    if deliveries_to_optimize:
        optimized_route = optimize_route(RESTAURANT_COORDS, deliveries_to_optimize)
        # Por enquanto, apenas imprimimos a rota. No futuro, salvaremos no banco.

    # Confirma o recebimento de todos os eventos no final
    acknowledge_orders(access_token, events)

if __name__ == "__main__":
    main()

