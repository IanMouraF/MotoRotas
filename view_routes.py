import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path para resolver os imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa a função para buscar as rotas do banco de dados
from database.manager import get_all_created_routes

if __name__ == "__main__":
    print("Buscando todas as rotas salvas no banco de dados...")
    
    all_routes = get_all_created_routes()
    
    if not all_routes:
        print("Nenhuma rota encontrada no banco de dados.")
    else:
        print(f"\n--- {len(all_routes)} Rota(s) Encontrada(s) ---\n")
        
        for route in all_routes:
            print(f"-> Rota ID: {route['id']} (Status: {route['status']})")
            print("   Pedidos na rota (em ordem de entrega):")
            for order in route['orders']:
                print(f"     - Sequência {order['sequence']}: Pedido ID {order['id']}")
            print(f"   Link de Navegação: {route['google_maps_link']}\n")