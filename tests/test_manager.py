import pytest
import os
import sys
import sqlite3
import database.manager

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.manager import save_new_order, get_pending_orders, setup_database

@pytest.fixture(scope='function')
def db_test_file(tmp_path, monkeypatch):
    """
    Cria um arquivo de banco de dados temporário e configura o manager para usá-lo.
    """
    # 1. Define o caminho do arquivo temporário
    d = tmp_path / "test_db"
    d.mkdir() # Garante que o diretório existe
    db_file = str(d / "test_motorotas.db")

    # 2. Remove a variável de ambiente DATABASE_URL para forçar SQLite
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # 3. Define uma função mock que retorna a conexão para o nosso arquivo temporário
    def mock_get_db_connection():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    # 4. Substitui a função get_db_connection original pela nossa mock
    monkeypatch.setattr(database.manager, 'get_db_connection', mock_get_db_connection)

    # 5. Inicializa o banco (cria tabelas no arquivo temporário)
    # Como fizemos o patch da função get_db_connection, o setup_database usará nosso banco de teste
    setup_database()

    return db_file

def test_save_new_order_success(db_test_file):
    """Verifica se um novo pedido é salvo com sucesso."""
    order_data = {'id': 'order_123', 'lat': -23.5, 'lon': -46.6}
    result = save_new_order(order_data)
    assert result is True

    # Verifica diretamente no banco
    conn = sqlite3.connect(db_test_file)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM orders WHERE id = ?", ('order_123',))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == 'order_123'
    assert row[1] == 'pending'

def test_save_new_order_duplicate(db_test_file):
    """Verifica se impede duplicatas."""
    order_data = {'id': 'order_456', 'lat': -23.6, 'lon': -46.7}
    save_new_order(order_data) # Salva 1ª vez
    
    result = save_new_order(order_data) # Tenta 2ª vez
    assert result is False

def test_get_pending_orders(db_test_file):
    """Verifica filtro de pedidos pendentes."""
    # Salva um pendente
    save_new_order({'id': 'pendente', 'lat': 1.0, 'lon': 1.0})
    
    # Insere manualmente um 'routed'
    conn = sqlite3.connect(db_test_file)
    conn.execute("INSERT INTO orders (id, lat, lon, status) VALUES (?, ?, ?, ?)", 
                 ('roteado', 2.0, 2.0, 'routed'))
    conn.commit()
    conn.close()
    
    pending = get_pending_orders()
    assert len(pending) == 1
    assert pending[0]['id'] == 'pendente'