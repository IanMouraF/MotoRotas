import os
import time
from dotenv import load_dotenv
import requests

# Adiciona o diretório raiz ao sys.path para importações
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import save_new_order

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações da API ---
CLIENT_ID = os.getenv("IFOOD_CLIENT_ID")
CLIENT_SECRET = os.getenv("IFOOD_CLIENT_SECRET")
BASE_API_URL = "https://merchant-api.ifood.com.br"

# --- Funções de Interação com a API ---

def get_ifood_token():
    """Autentica na API do iFood e retorna o token de acesso."""
    auth_url = f"{BASE_API_URL}/authentication/v1.0/oauth/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grantType': 'client_credentials',
        'clientId': CLIENT_ID,
        'clientSecret': CLIENT_SECRET
    }
    response = requests.post(auth_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get('accessToken')
    else:
        print(f"❌ Coletor: Falha na autenticação! Status: {response.status_code}")
        return None

def get_new_orders(token):
    """Busca por novos eventos (pedidos) na API."""
    orders_url = f"{BASE_API_URL}/order/v1.0/events:polling"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(orders_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 204: # No Content
        return []
    else:
        print(f"❌ Coletor: Erro ao buscar pedidos: Status {response.status_code}")
        return None

def get_order_details(token, order_id):
    """Busca os detalhes de um pedido específico."""
    details_url = f"{BASE_API_URL}/order/v1.0/orders/{order_id}"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(details_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Coletor: Erro ao buscar detalhes do pedido {order_id}: Status {response.status_code}")
        return None

def acknowledge_orders(token, events):
    """Confirma o recebimento dos eventos para a API do iFood."""
    ack_url = f"{BASE_API_URL}/order/v1.0/events/acknowledgment"
    headers = {'Authorization': f'Bearer {token}'}
    data = [{'id': event['id']} for event in events]
    response = requests.post(ack_url, headers=headers, json=data)
    return response.status_code == 202

def main_loop():
    """Função principal que executa um ciclo de coleta."""
    token = get_ifood_token()
    if not token:
        return

    events = get_new_orders(token)

    if events is None: # Ocorreu um erro na requisição
        return

    if not events:
        # Nenhum pedido novo, o loop continua silenciosamente
        return

    print(f"✅ Coletor: Encontrado(s) {len(events)} novo(s) evento(s)!")
    
    new_orders_to_ack = []
    for event in events:
        order_id = event.get('orderId')
        if order_id:
            details = get_order_details(token, order_id)
            if details and details.get('delivery'):
                address = details['delivery']['deliveryAddress']
                coords = address['coordinates']
                
                order_data = {
                    'id': order_id,
                    'lat': coords['latitude'],
                    'lon': coords['longitude']
                }
                
                if save_new_order(order_data):
                    new_orders_to_ack.append(event)
            else:
                print(f"   -> Pedido {order_id} sem informações de entrega. Ignorando.")

    if new_orders_to_ack:
        print("   Confirmando recebimento dos eventos...")
        if acknowledge_orders(token, new_orders_to_ack):
            print("   -> Eventos confirmados com sucesso!")
        else:
            print("   -> Falha ao confirmar eventos.")

if __name__ == "__main__":
    POLLING_INTERVAL_SECONDS = 3
    print("--- INICIANDO COLETOR DE PEDIDOS (Pressione Ctrl+C para parar) ---")
    while True:
        try:
            main_loop()
            time.sleep(POLLING_INTERVAL_SECONDS)
        except Exception as e:
            print(f"\n🚨 Coletor: Ocorreu um erro inesperado no loop: {e}")
            print(f"--- Tentando novamente em {POLLING_INTERVAL_SECONDS} segundos ---")
            time.sleep(POLLING_INTERVAL_SECONDS)

