import os
import requests
from dotenv import load_dotenv

# Importa nosso gerenciador de banco de dados
from database.manager import save_new_order

# Carrega as variáveis de ambiente
load_dotenv()

# --- CONFIGURAÇÕES ---
CLIENT_ID = os.getenv("IFOOD_CLIENT_ID")
CLIENT_SECRET = os.getenv("IFOOD_CLIENT_SECRET")
AUTH_API_URL = "https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token"
ORDER_API_URL = "https://merchant-api.ifood.com.br/order/v1.0"

# --- FUNÇÕES DE API ---

def authenticate():
    print("1. Tentando autenticar na API do iFood...")
    # ... (código de autenticação inalterado) ...
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
    print("\n2. Buscando por novos pedidos...")
    # ... (código de busca de pedidos inalterado) ...
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
    print(f"   - Buscando detalhes do pedido {order_id}...")
    # ... (código de detalhes do pedido inalterado) ...
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{ORDER_API_URL}/orders/{order_id}", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"   - ❌ Erro ao buscar detalhes do pedido {order_id}! Código: {response.status_code}")
        return None

def acknowledge_orders(token, events):
    print("\n4. Confirmando recebimento dos eventos para o iFood...")
    # ... (código de confirmação inalterado) ...
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
            print("\n3. Coletando e salvando informações dos pedidos...")
            for event in events:
                if event.get('code') == 'PLC':
                    order_id = event.get('orderId')
                    details = get_order_details(access_token, order_id)
                    if details and details.get('delivery', {}).get('deliveryAddress'):
                        address = details['delivery']['deliveryAddress']
                        coordinates = address.get('coordinates', {})
                        
                        # Prepara os dados para salvar no BD
                        order_data = {
                            "id": order_id,
                            "lat": coordinates.get('latitude', 0.0),
                            "lon": coordinates.get('longitude', 0.0)
                        }
                        # Salva o pedido no nosso banco de dados
                        save_new_order(order_data)
            
            # Confirma os eventos para o iFood (agora que já salvamos)
            acknowledge_orders(access_token, events)

