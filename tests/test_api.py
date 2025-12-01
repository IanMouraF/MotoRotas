import pytest
import os
import sqlite3
import app.database.manager 
from app import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Configura um cliente Flask de teste conectado a um banco de dados temporário.
    """
    # 1. Define o caminho de um banco de dados temporário isolado
    d = tmp_path / "test_db_api"
    d.mkdir()
    db_file = str(d / "api_test.db")

    # 2. Garante que não estamos tentando usar Postgres
    monkeypatch.delenv("DATABASE_URL", raising=False)
    
    # 3. Cria a função falsa de conexão
    def mock_get_db_connection():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    # 4. Aplica o "golpe" (monkeypatch) para o app usar nossa conexão falsa
    monkeypatch.setattr(app.database.manager, 'get_db_connection', mock_get_db_connection)

    # 5. PASSO CRÍTICO QUE FALTAVA: Criar as tabelas no banco temporário
    app.database.manager.setup_database()

    # 6. Cria o app Flask e retorna o cliente de testes
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    
    with flask_app.test_client() as client:
        yield client

def test_get_routes_empty(client):
    """Verifica se retorna uma lista vazia quando não há rotas."""
    response = client.get('/api/routes')
    assert response.status_code == 200
    assert response.json == []

def test_get_routes_with_data(client):
    """Verifica se retorna dados corretamente quando há rotas."""
    # Importe também o save_new_order
    from app.database.manager import create_new_route, save_new_order
    
    order = {'id': 'pedido_teste_api', 'lat': -3.7, 'lon': -38.5}
    restaurant = {'lat': -3.7, 'lon': -38.5}
    
    # 1. CRÍTICO: Salva o pedido no banco antes de usá-lo
    save_new_order(order)
    
    # 2. Agora sim cria a rota associada a esse pedido
    create_new_route(order, restaurant)
    
    # Chama a API
    response = client.get('/api/routes')
    
    assert response.status_code == 200
    assert len(response.json) == 1
    # Agora a lista não estará vazia
    assert response.json[0]['orders'][0]['id'] == 'pedido_teste_api'