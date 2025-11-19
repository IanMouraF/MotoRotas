import sqlite3
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(PROJECT_ROOT)

DB_PATH = os.path.join(PROJECT_ROOT, 'motorotas.db')

def clear_routes_and_reset_orders():
    """
    Deleta todas as rotas e reseta o status dos pedidos de 'routed' para 'pending'.
    """
    if not os.path.exists(DB_PATH):
        print("Banco de dados não encontrado. Nada a fazer.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Limpando rotas e resetando pedidos...")

        # 1. Deleta as associações entre rotas e pedidos
        cursor.execute("DELETE FROM route_orders")
        print("  -> Associações de rotas deletadas.")

        # 2. Deleta as rotas em si
        cursor.execute("DELETE FROM routes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='routes'")
        print("  -> Rotas deletadas.")

        # 3. Reseta o status dos pedidos que já estavam em uma rota
        cursor.execute("UPDATE orders SET status = 'pending' WHERE status = 'routed'")
        updated_count = cursor.rowcount
        print(f"  -> Status de {updated_count} pedido(s) revertido para 'pending'.")

        conn.commit()
        print("\n✅ Operação de reset concluída com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ocorreu um erro: {e}")
    finally:
        conn.close()

def clear_all_data():
    """
    Deleta TODAS as rotas e TODOS os pedidos do banco de dados.
    """
    if not os.path.exists(DB_PATH):
        print("Banco de dados não encontrado. Nada a fazer.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("DELETANDO TODOS OS DADOS...")

        # Deleta em ordem para respeitar as chaves estrangeiras
        cursor.execute("DELETE FROM route_orders")
        print("  -> Associações de rotas deletadas.")
        
        cursor.execute("DELETE FROM routes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='routes'")
        print("  -> Rotas deletadas.")

        cursor.execute("DELETE FROM orders")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
        print("  -> Pedidos deletados.")

        conn.commit()
        print("\n✅ Todos os dados foram deletados permanentemente.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ocorreu um erro: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Pede confirmação inicial
    confirm = input("Você tem certeza que deseja limpar o banco de dados? (s/n): ")
    if confirm.lower() == 's':
        # Pede para escolher a ação
        action = input("O que fazer com os pedidos? [r]esetar para 'pending' ou [d]eletar permanentemente? (r/d): ")
        
        if action.lower() == 'r':
            clear_routes_and_reset_orders()
        
        elif action.lower() == 'd':
            # Confirmação extra para uma ação destrutiva
            confirm_delete = input("ATENÇÃO: Isso apagará TODOS os pedidos permanentemente. Continuar? (s/n): ")
            if confirm_delete.lower() == 's':
                clear_all_data()
            else:
                print("Operação de exclusão cancelada.")
        
        else:
            print("Opção inválida. Operação cancelada.")
            
    else:
        print("Operação cancelada.")

