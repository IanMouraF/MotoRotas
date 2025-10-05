import os
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# URLs da API do iFood
AUTH_API_URL = 'https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token'
ORDER_API_URL = 'https://merchant-api.ifood.com.br/order/v1.0'

# Pega as credenciais do arquivo .env
CLIENT_ID = os.getenv('IFOOD_CLIENT_ID')
CLIENT_SECRET = os.getenv('IFOOD_CLIENT_SECRET')

def get_ifood_token():
    """
    Função para obter o token de acesso da API do iFood.
    Retorna o token de acesso se for bem-sucedido, senão retorna None.
    """
    print('1. Tentando autenticar na API do iFood...')

    if not CLIENT_ID or not CLIENT_SECRET:
        print('❌ Erro: As credenciais IFOOD_CLIENT_ID e IFOOD_CLIENT_SECRET não foram encontradas no arquivo .env')
        return None

    payload = {
        'grantType': 'client_credentials',
        'clientId': CLIENT_ID,
        'clientSecret': CLIENT_SECRET
    }
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }

    try:
        response = requests.post(AUTH_API_URL, data=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get('accessToken')
        print('✅ Autenticação bem-sucedida!')
        return access_token
    except requests.exceptions.HTTPError as http_err:
        print(f'❌ Falha na autenticação! Erro HTTP:')
        try:
            print('Detalhes do erro:', http_err.response.json())
        except ValueError:
            print('Não foi possível decodificar a resposta de erro:', http_err.response.text)
        return None
    except Exception as err:
        print(f'❌ Ocorreu um outro erro na autenticação: {err}')
        return None

def get_new_orders(token):
    """
    Busca por novos eventos de pedidos na API.
    """
    if not token:
        return []

    print('\n2. Buscando por novos pedidos...')
    headers = { 'Authorization': f'Bearer {token}' }
    
    try:
        response = requests.get(f'{ORDER_API_URL}/events:polling', headers=headers)

        if response.status_code == 204:
            print('✅ Nenhum pedido novo encontrado.')
            return []

        response.raise_for_status()
        orders = response.json()
        
        if not orders:
            print('✅ Nenhum pedido novo encontrado.')
        else:
            print(f'✅ Encontrado(s) {len(orders)} novo(s) evento(s)!')
            for order in orders:
                print(f"  - Evento ID: {order.get('id')}, Código: {order.get('code')}, Pedido ID: {order.get('orderId')}")
        return orders
    except requests.exceptions.HTTPError as http_err:
        print(f'❌ Erro ao buscar pedidos! HTTP:')
        try:
            print('Detalhes do erro:', http_err.response.json())
        except ValueError:
            print('Não foi possível decodificar a resposta de erro:', http_err.response.text)
        return []
    except Exception as err:
        print(f'❌ Ocorreu um outro erro ao buscar pedidos: {err}')
        return []

def get_order_details(order_id, token):
    """
    Busca os detalhes de um pedido específico, incluindo o endereço.
    """
    if not order_id or not token:
        return

    print(f'\n3. Buscando detalhes do pedido {order_id}...')
    headers = { 'Authorization': f'Bearer {token}' }

    try:
        response = requests.get(f'{ORDER_API_URL}/orders/{order_id}', headers=headers)
        response.raise_for_status()
        details = response.json()

        # Extrai as informações de entrega
        delivery_info = details.get('delivery')
        if delivery_info:
            address = delivery_info.get('deliveryAddress')
            coordinates = address.get('coordinates', {})
            
            print('✅ Detalhes do endereço encontrados:')
            print(f"   Rua: {address.get('streetName')}, {address.get('streetNumber')}")
            print(f"   Bairro: {address.get('neighborhood')}, Cidade: {address.get('city')}")
            print(f"   CEP: {address.get('postalCode')}")
            print(f"   Latitude: {coordinates.get('latitude')}")
            print(f"   Longitude: {coordinates.get('longitude')}")
        else:
            print('⚠️ Não foi possível encontrar informações de entrega para este pedido.')

    except requests.exceptions.HTTPError as http_err:
        print(f'❌ Erro ao buscar detalhes do pedido! HTTP:')
        try:
            print('Detalhes do erro:', http_err.response.json())
        except ValueError:
            print('Não foi possível decodificar a resposta de erro:', http_err.response.text)
    except Exception as err:
        print(f'❌ Ocorreu um outro erro ao buscar detalhes do pedido: {err}')

def acknowledge_orders(events, token):
    """
    Confirma o recebimento dos eventos para que não sejam enviados novamente.
    """
    if not events or not token:
        return

    print('\n4. Confirmando recebimento dos eventos...')
    
    ids_to_acknowledge = [{'id': event['id']} for event in events]
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(f'{ORDER_API_URL}/events/acknowledgment', json=ids_to_acknowledge, headers=headers)
        response.raise_for_status()
        print('✅ Eventos confirmados com sucesso!')
    except requests.exceptions.HTTPError as http_err:
        print(f'❌ Erro ao confirmar eventos! HTTP:')
        try:
            print('Detalhes do erro:', http_err.response.json())
        except ValueError:
            print('Não foi possível decodificar a resposta de erro:', http_err.response.text)
    except Exception as err:
        print(f'❌ Ocorreu um outro erro ao confirmar eventos: {err}')

# Ponto de entrada do script
if __name__ == '__main__':
    access_token = get_ifood_token()
    
    if access_token:
        new_events = get_new_orders(access_token)
        
        if new_events:
            for event in new_events:
                # O código 'PLC' (Placed) indica um novo pedido.
                if event.get('code') == 'PLC':
                    order_id = event.get('orderId')
                    if order_id:
                        # Busca os detalhes de cada novo pedido.
                        get_order_details(order_id, access_token)
            
            # Confirma todos os eventos processados de uma vez.
            acknowledge_orders(new_events, access_token)

