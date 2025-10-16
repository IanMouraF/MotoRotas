# Este arquivo é o nosso antigo main.py, refatorado para ser um módulo.

import os
import time
from dotenv import load_dotenv
import requests
import sys

# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.manager import save_new_order

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações da API ---
CLIENT_ID = os.getenv("IFOOD_CLIENT_ID")
CLIENT_SECRET = os.getenv("IFOOD_CLIENT_SECRET")
BASE_API_URL = "https://merchant-api.ifood.com.br"

def get_ifood_token():
    auth_url = f"{BASE_API_URL}/authentication/v1.0/oauth/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grantType': 'client_credentials', 'clientId': CLIENT_ID, 'clientSecret': CLIENT_SECRET}
    try:
        response = requests.post(auth_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.json().get('accessToken')
    except requests.RequestException as e:
        print(f"❌ Coletor: Falha na autenticação! {e}")
        return None

def get_new_orders(token):
    orders_url = f"{BASE_API_URL}/order/v1.0/events:polling"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(orders_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return []
        else:
            print(f"❌ Coletor: Erro ao buscar pedidos: Status {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"❌ Coletor: Erro de conexão ao buscar pedidos: {e}")
        return None

def get_order_details(token, order_id):
    details_url = f"{BASE_API_URL}/order/v1.0/orders/{order_id}"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(details_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Coletor: Erro ao buscar detalhes do pedido {order_id}: {e}")
        return None

def acknowledge_orders(token, events):
    ack_url = f"{BASE_API_URL}/order/v1.0/events/acknowledgment"
    headers = {'Authorization': f'Bearer {token}'}
    data = [{'id': event['id']} for event in events]
    try:
        response = requests.post(ack_url, headers=headers, json=data, timeout=10)
        return response.status_code == 202
    except requests.RequestException as e:
        print(f"❌ Coletor: Erro ao confirmar eventos: {e}")
        return False

def collector_cycle():
    """Executa um único ciclo de coleta de pedidos."""
    token = get_ifood_token()
    if not token:
        return

    events = get_new_orders(token)
    if events is None:
        return

    if not events:
        return # Continua silenciosamente

    print(f"✅ Coletor: {len(events)} novo(s) evento(s) encontrado(s)!")
    
    new_orders_to_ack = []
    for event in events:
        order_id = event.get('orderId')
        if order_id:
            details = get_order_details(token, order_id)
            if details and details.get('delivery'):
                address = details['delivery']['deliveryAddress']
                coords = address['coordinates']
                
                order_data = {'id': order_id, 'lat': coords['latitude'], 'lon': coords['longitude']}
                if save_new_order(order_data):
                    new_orders_to_ack.append(event)

    if new_orders_to_ack:
        if not acknowledge_orders(token, new_orders_to_ack):
            print("   -> Falha ao confirmar eventos.")

def start_collector_loop():
    """Inicia o loop infinito do coletor."""
    interval = 3
    print(f"--- COLETOR DE PEDIDOS INICIADO (verificando a cada {interval}s) ---")
    while True:
        try:
            collector_cycle()
            time.sleep(interval)
        except Exception as e:
            print(f"\n🚨 Coletor: Erro inesperado no loop: {e}")
            time.sleep(interval)
