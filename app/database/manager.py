import sqlite3
import os
import psycopg2
from psycopg2.extras import DictCursor

# Define o caminho da base de dados na raiz do projeto (Padrão para SQLite)
# Isso deve estar no nível superior do módulo para ser acessível pelo monkeypatch
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'motorotas.db')

# --- LÓGICA DE CONEXÃO INTELIGENTE ---
# Esta função agora usa a URL do PostgreSQL se estiver no Render (produção),
# ou volta a usar o arquivo SQLite se estiver rodando localmente (desenvolvimento).
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados apropriado."""
    db_url = os.getenv("DATABASE_URL")
    
    # Se DATABASE_URL estiver definido e não for vazio, usa PostgreSQL
    if db_url:
        # Estamos em produção (Render), conectar ao PostgreSQL
        return psycopg2.connect(db_url)
    else:
        # Estamos em desenvolvimento local, usar SQLite
        # Importante: usamos a variável global DB_PATH aqui
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
        return conn

def setup_database():
    """Cria as tabelas do banco de dados se elas não existirem, com sintaxe compatível."""
    # ... (código da função setup_database continua igual) ...
    print("Verificando e configurando o banco de dados...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    is_postgres = isinstance(conn, psycopg2.extensions.connection)
    
    # Sintaxe de autoincremento varia entre SQLite e PostgreSQL
    autoincrement_syntax = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    text_syntax = "VARCHAR(255)" if is_postgres else "TEXT"
    
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS orders (
        id {text_syntax} PRIMARY KEY,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        status {text_syntax} NOT NULL DEFAULT 'pending'
    )
    ''')
    
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS routes (
        id {autoincrement_syntax},
        google_maps_link TEXT,
        status {text_syntax} NOT NULL DEFAULT 'created'
    )
    ''')
    
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS route_orders (
        route_id INTEGER,
        order_id {text_syntax},
        delivery_sequence INTEGER,
        FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
        PRIMARY KEY (route_id, order_id)
    )
    ''')
    
    # NOVA TABELA: Tabela para guardar os motoboys
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS motoboys (
        id {autoincrement_syntax},
        name {text_syntax} NOT NULL,
        status {text_syntax} NOT NULL DEFAULT 'unavailable'
    )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    # print("Banco de dados pronto.") # Comentado para limpar output dos testes

def _get_placeholder(conn):
    """Retorna o placeholder correto para o tipo de conexão."""
    return "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"

def save_new_order(order_data):
    """Salva um novo pedido no banco de dados, evitando duplicatas."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    sql = f"INSERT INTO orders (id, lat, lon, status) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})"
    
    try:
        # with conn: # Removido para compatibilidade com psycopg2 que gerencia transações diferente
        cursor = conn.cursor()
        try:
            cursor.execute(sql, (order_data['id'], order_data['lat'], order_data['lon'], 'pending'))
            conn.commit()
            # print(f"   -> Pedido {order_data['id']} salvo com sucesso.")
            return True
        except (sqlite3.IntegrityError, psycopg2.IntegrityError):
            conn.rollback()
            return False
        finally:
            cursor.close()
    finally:
        if conn:
            conn.close()

def _rows_to_dicts(cursor, rows):
    """Converte uma lista de tuplas/rows em uma lista de dicionários."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

def get_pending_orders():
    """Busca todos os pedidos com status 'pending'."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, lat, lon FROM orders WHERE status = 'pending'")
            rows = cursor.fetchall()
            orders = _rows_to_dicts(cursor, rows)
        finally:
            cursor.close()
    finally:
        conn.close()
    return [{"id": o['id'], "coords": {"lat": o['lat'], "lon": o['lon']}} for o in orders]

# ... (Outras funções: get_created_routes, create_new_route, update_route, get_all_created_routes continuam iguais) ...
# Apenas certifique-se de que elas usam get_db_connection() corretamente.

# Importante: Comente ou remova a chamada automática para setup_database() no final do arquivo
# para evitar que ela rode ao importar o módulo nos testes sem o monkeypatch estar ativo.
# setup_database()