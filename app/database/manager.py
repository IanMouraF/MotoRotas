import sqlite3
import os
import psycopg2
from psycopg2.extras import DictCursor

# Define o caminho da base de dados na raiz do projeto (Padrão para SQLite)
# Isso deve estar no nível superior do módulo para ser acessível pelo monkeypatch
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'motorotas.db')

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

# --- FUNÇÕES QUE FALTAVAM ---

def get_created_routes():
    """Busca todas as rotas com status 'created' para o otimizador."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        try:
            # Busca as rotas
            sql_routes = f"SELECT * FROM routes WHERE status = 'created'"
            cursor.execute(sql_routes)
            routes_rows = _rows_to_dicts(cursor, cursor.fetchall())
            
            routes = []
            for r in routes_rows:
                route_obj = dict(r)
                # Busca os pedidos dessa rota
                sql_orders = f'''
                    SELECT o.id, o.lat, o.lon, ro.delivery_sequence 
                    FROM orders o
                    JOIN route_orders ro ON o.id = ro.order_id
                    WHERE ro.route_id = {placeholder}
                    ORDER BY ro.delivery_sequence
                '''
                cursor.execute(sql_orders, (route_obj['id'],))
                orders_rows = _rows_to_dicts(cursor, cursor.fetchall())
                
                route_obj['orders'] = [
                    {'id': o['id'], 'coords': {'lat': o['lat'], 'lon': o['lon']}} 
                    for o in orders_rows
                ]
                routes.append(route_obj)
            return routes
        finally:
            cursor.close()
    finally:
        conn.close()

def get_all_created_routes():
    """Busca TODAS as rotas (para a API/Visualização), independente do status."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM routes")
            routes_rows = _rows_to_dicts(cursor, cursor.fetchall())
            
            routes = []
            for r in routes_rows:
                route_obj = dict(r)
                sql_orders = f'''
                    SELECT o.id, o.lat, o.lon, ro.delivery_sequence 
                    FROM orders o
                    JOIN route_orders ro ON o.id = ro.order_id
                    WHERE ro.route_id = {placeholder}
                    ORDER BY ro.delivery_sequence
                '''
                cursor.execute(sql_orders, (route_obj['id'],))
                orders_rows = _rows_to_dicts(cursor, cursor.fetchall())
                
                route_obj['orders'] = [
                    {'id': o['id'], 'sequence': o['delivery_sequence'], 'coords': {'lat': o['lat'], 'lon': o['lon']}} 
                    for o in orders_rows
                ]
                routes.append(route_obj)
            return routes
        finally:
            cursor.close()
    finally:
        conn.close()

def create_new_route(first_order, restaurant_coords):
    """Cria uma nova rota no banco de dados com um pedido inicial."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        try:
            # 1. Cria a rota
            # Nota: PostgreSQL usa RETURNING id, SQLite não. 
            # Para simplificar aqui, faremos insert e depois select last_insert_rowid ou similar se for sqlite
            
            is_postgres = isinstance(conn, psycopg2.extensions.connection) if 'psycopg2' in globals() else False
            
            if is_postgres:
                cursor.execute("INSERT INTO routes (status) VALUES ('created') RETURNING id")
                route_id = cursor.fetchone()[0]
            else:
                cursor.execute("INSERT INTO routes (status) VALUES ('created')")
                route_id = cursor.lastrowid

            # 2. Associa o pedido à rota
            sql_assoc = f"INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES ({placeholder}, {placeholder}, 1)"
            cursor.execute(sql_assoc, (route_id, first_order['id']))
            
            # 3. Atualiza status do pedido
            sql_update = f"UPDATE orders SET status = 'routed' WHERE id = {placeholder}"
            cursor.execute(sql_update, (first_order['id'],))
            
            conn.commit()
            return route_id
        except Exception as e:
            conn.rollback()
            print(f"Erro ao criar rota: {e}")
            raise e
        finally:
            cursor.close()
    finally:
        conn.close()

def update_route(route_data):
    """Atualiza uma rota existente (link e lista de pedidos)."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        try:
            # 1. Atualiza o link da rota
            sql_route = f"UPDATE routes SET google_maps_link = {placeholder} WHERE id = {placeholder}"
            cursor.execute(sql_route, (route_data.get('google_maps_link'), route_data['id']))
            
            # 2. Remove associações antigas dessa rota (para recriar na nova ordem)
            # Nota: Isso é uma estratégia simples. Em produção, poderia ser mais otimizado.
            sql_delete = f"DELETE FROM route_orders WHERE route_id = {placeholder}"
            cursor.execute(sql_delete, (route_data['id'],))
            
            # 3. Reinsere os pedidos na nova ordem
            for index, order in enumerate(route_data['orders']):
                sequence = index + 1
                sql_assoc = f"INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES ({placeholder}, {placeholder}, {placeholder})"
                cursor.execute(sql_assoc, (route_data['id'], order['id'], sequence))
                
                # Garante que o status do pedido esteja 'routed'
                sql_update_order = f"UPDATE orders SET status = 'routed' WHERE id = {placeholder}"
                cursor.execute(sql_update_order, (order['id'],))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Erro ao atualizar rota: {e}")
            raise e
        finally:
            cursor.close()
    finally:
        conn.close()