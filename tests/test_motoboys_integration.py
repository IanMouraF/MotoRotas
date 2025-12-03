import pytest
import sqlite3
import os
import sys

# Garante que o Python encontre o app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
import app.database.manager

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Configura um cliente de teste com banco limpo e tabelas atualizadas.
    """
    # 1. Banco temporário
    d = tmp_path / "test_db_motoboy"
    d.mkdir()
    db_file = str(d / "motoboy_test.db")

    # 2. Mock da conexão
    monkeypatch.delenv("DATABASE_URL", raising=False)
    def mock_get_db_connection():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    monkeypatch.setattr(app.database.manager, 'get_db_connection', mock_get_db_connection)

    # 3. Cria TODAS as tabelas (incluindo motoboys e colunas novas)
    app.database.manager.setup_database()

    # 4. App Flask
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    
    with flask_app.test_client() as client:
        yield client

def test_crud_motoboy(client):
    """Testa criar e listar motoboys."""
    # 1. Cria Motoboy
    response = client.post('/api/motoboys', json={
        "name": "Carlos Entregador",
        "phone": "85999998888"
    })
    assert response.status_code == 201
    
    # 2. Lista Motoboys
    response = client.get('/api/motoboys')
    assert response.status_code == 200
    data = response.json
    assert len(data) == 1
    assert data[0]['name'] == "Carlos Entregador"
    assert data[0]['status'] == "available"

def test_assign_route_flow(client):
    """Testa o fluxo de atribuir uma rota a um motoboy."""
    # Imports internos para preparar o cenário
    from app.database.manager import create_new_route, save_new_order, create_motoboy
    
    # 1. Preparação (Cria Motoboy e Rota no banco)
    create_motoboy("João Rápido", "85999111111") # ID 1 (provavelmente)
    
    order = {'id': 'pedido_assign', 'lat': -3.7, 'lon': -38.5}
    rest = {'lat': -3.7, 'lon': -38.5}
    save_new_order(order)
    route_id = create_new_route(order, rest) # Retorna o ID da rota
    
    # 2. Chama a API para atribuir
    response = client.post(f'/api/routes/{route_id}/assign', json={
        "motoboy_id": 1
    })
    
    assert response.status_code == 200
    assert "sucesso" in response.json['message']

    # 3. Verifica se o status do motoboy mudou para 'delivering'
    # Vamos checar chamando a API de lista novamente
    response = client.get('/api/motoboys')
    motoboys = response.json
    
    joao = next(m for m in motoboys if m['name'] == "João Rápido")
    assert joao['status'] == "delivering"