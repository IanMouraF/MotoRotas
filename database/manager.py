import sqlite3
import os
import psycopg2
from psycopg2.extras import DictCursor

# --- LÓGICA DE CONEXÃO INTELIGENTE ---
# Esta função agora usa a URL do PostgreSQL se estiver no Render (produção),
# ou volta a usar o arquivo SQLite se estiver rodando localmente (desenvolvimento).
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados apropriado."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Estamos em produção (Render), conectar ao PostgreSQL
        return psycopg2.connect(db_url)
    else:
        # Estamos em desenvolvimento local, usar SQLite
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'motorotas.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
        return conn

def setup_database():
    """Cria as tabelas do banco de dados se elas não existirem, com sintaxe compatível."""
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

    conn.commit()
    cursor.close()
    conn.close()
    print("Banco de dados pronto.")

def _get_placeholder(conn):
    """Retorna o placeholder correto para o tipo de conexão."""
    return "%s" if isinstance(conn, psycopg2.extensions.connection) else "?"

def save_new_order(order_data):
    """Salva um novo pedido no banco de dados, evitando duplicatas."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    sql = f"INSERT INTO orders (id, lat, lon, status) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})"
    
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (order_data['id'], order_data['lat'], order_data['lon'], 'pending'))
        print(f"   -> Pedido {order_data['id']} salvo com sucesso.")
        return True
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return False
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
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, lat, lon FROM orders WHERE status = 'pending'")
            rows = cursor.fetchall()
            orders = _rows_to_dicts(cursor, rows)
    finally:
        conn.close()
    return [{"id": o['id'], "coords": {"lat": o['lat'], "lon": o['lon']}} for o in orders]

def get_created_routes():
    """Busca todas as rotas com status 'created' e os pedidos associados."""
    conn = get_db_connection()
    query = '''
        SELECT r.id as route_id, r.google_maps_link, r.status as route_status,
               ro.order_id, ro.delivery_sequence, o.lat, o.lon
        FROM routes r
        JOIN route_orders ro ON r.id = ro.route_id
        JOIN orders o ON ro.order_id = o.id
        WHERE r.status = 'created'
        ORDER BY r.id, ro.delivery_sequence
    '''
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        conn.close()

    routes = {}
    for row in rows:
        route_id = row['route_id']
        if route_id not in routes:
            routes[route_id] = {'id': route_id, 'status': row['route_status'], 'google_maps_link': row['google_maps_link'], 'orders': []}
        routes[route_id]['orders'].append({'id': row['order_id'], 'sequence': row['delivery_sequence'], 'coords': {'lat': row['lat'], 'lon': row['lon']}})
    return list(routes.values())

def create_new_route(order, restaurant_coords):
    """Cria uma nova rota com um único pedido inicial."""
    from routing.optimizer import create_google_maps_link
    conn = get_db_connection()
    p = _get_placeholder(conn)
    gmaps_link = create_google_maps_link(restaurant_coords, [order])
    route_id = None
    
    is_postgres = isinstance(conn, psycopg2.extensions.connection)
    
    try:
        with conn.cursor() as cursor:
            sql_route = f"INSERT INTO routes (google_maps_link, status) VALUES ({p}, {p})"
            if is_postgres:
                sql_route += " RETURNING id"
            
            cursor.execute(sql_route, (gmaps_link, 'created'))
            
            if is_postgres:
                route_id = cursor.fetchone()[0]
            else:
                route_id = cursor.lastrowid

            cursor.execute(f"INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES ({p}, {p}, {p})", (route_id, order['id'], 1))
            cursor.execute(f"UPDATE orders SET status = 'routed' WHERE id = {p}", (order['id'],))
        conn.commit()
    finally:
        conn.close()
    return route_id

def update_route(route_data):
    """Atualiza uma rota existente, adicionando ou reordenando pedidos."""
    conn = get_db_connection()
    p = _get_placeholder(conn)
    route_id = route_data['id']
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE routes SET google_maps_link = {p} WHERE id = {p}", (route_data['google_maps_link'], route_id))
            cursor.execute(f"DELETE FROM route_orders WHERE route_id = {p}", (route_id,))
            
            order_ids_to_update = []
            for i, order in enumerate(route_data['orders']):
                order_id = order['id']
                order_ids_to_update.append(order_id)
                cursor.execute(f"INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES ({p}, {p}, {p})", (route_id, order_id, i + 1))

            placeholders = ', '.join([p] * len(order_ids_to_update))
            cursor.execute(f"UPDATE orders SET status = 'routed' WHERE id IN ({placeholders})", order_ids_to_update)
        conn.commit()
    finally:
        conn.close()

def get_all_created_routes():
    """Busca todas as rotas criadas e os pedidos associados a elas."""
    conn = get_db_connection()
    query = '''
        SELECT r.id as route_id, r.google_maps_link, r.status as route_status,
               ro.order_id, ro.delivery_sequence
        FROM routes r
        JOIN route_orders ro ON r.id = ro.route_id
        ORDER BY r.id, ro.delivery_sequence
    '''
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        conn.close()

    routes = {}
    for row in rows:
        route_id = row['route_id']
        if route_id not in routes:
            routes[route_id] = {'id': route_id, 'google_maps_link': row['google_maps_link'], 'status': row['route_status'], 'orders': []}
        routes[route_id]['orders'].append({'id': row['order_id'], 'sequence': row['delivery_sequence']})
    return list(routes.values())

# Executa a configuração inicial quando este módulo é importado pela primeira vez.
setup_database()