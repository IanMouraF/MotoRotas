import sqlite3
import os

# Define o caminho do banco de dados na raiz do projeto
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'motorotas.db')

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

def setup_database():
    """Cria as tabelas do banco de dados se elas não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela para armazenar os pedidos brutos que chegam do iFood
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- pending, routed, in_progress, delivered
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Tabela para armazenar as rotas geradas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT NOT NULL DEFAULT 'created', -- created, assigned, completed
        google_maps_link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Tabela para ligar os pedidos às rotas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS route_orders (
        route_id INTEGER,
        order_id TEXT,
        delivery_sequence INTEGER,
        FOREIGN KEY (route_id) REFERENCES routes (id),
        FOREIGN KEY (order_id) REFERENCES orders (id),
        PRIMARY KEY (route_id, order_id)
    )
    ''')

    conn.commit()
    conn.close()

def save_new_order(order_data):
    """Salva um novo pedido no banco de dados, evitando duplicatas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO orders (id, lat, lon, status) VALUES (?, ?, ?, ?)",
            (order_data['id'], order_data['lat'], order_data['lon'], 'pending')
        )
        conn.commit()
        print(f"   -> Pedido {order_data['id']} salvo no banco de dados.")
        return True
    except sqlite3.IntegrityError:
        print(f"   -> Pedido {order_data['id']} já existe no banco de dados. Ignorando.")
        return False
    finally:
        conn.close()

def get_pending_orders():
    """Busca todos os pedidos com status 'pending' no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, lat, lon FROM orders WHERE status = 'pending'")
    pending_orders = cursor.fetchall()
    conn.close()
    return [{"id": row['id'], "coords": {"lat": row['lat'], "lon": row['lon']}} for row in pending_orders]

def get_created_routes():
    """Busca todas as rotas com status 'created' e os pedidos associados a elas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            r.id as route_id, 
            r.google_maps_link, 
            r.status as route_status,
            ro.order_id,
            ro.delivery_sequence,
            o.lat,
            o.lon
        FROM routes r
        JOIN route_orders ro ON r.id = ro.route_id
        JOIN orders o ON ro.order_id = o.id
        WHERE r.status = 'created'
        ORDER BY r.id, ro.delivery_sequence
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    routes = {}
    for row in rows:
        route_id = row['route_id']
        if route_id not in routes:
            routes[route_id] = {
                'id': route_id,
                'status': row['route_status'],
                'google_maps_link': row['google_maps_link'],
                'orders': []
            }
        routes[route_id]['orders'].append({
            'id': row['order_id'],
            'sequence': row['delivery_sequence'],
            'coords': {'lat': row['lat'], 'lon': row['lon']}
        })
        
    return list(routes.values())

def create_new_route(order, restaurant_coords):
    """Cria uma nova rota com um único pedido inicial."""
    from routing.optimizer import create_google_maps_link
    conn = get_db_connection()
    cursor = conn.cursor()
    gmaps_link = create_google_maps_link(restaurant_coords, [order])

    try:
        cursor.execute("INSERT INTO routes (google_maps_link, status) VALUES (?, ?)", (gmaps_link, 'created'))
        route_id = cursor.lastrowid
        cursor.execute("INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES (?, ?, ?)", (route_id, order['id'], 1))
        cursor.execute("UPDATE orders SET status = 'routed' WHERE id = ?", (order['id'],))
        conn.commit()
        return route_id
    finally:
        conn.close()

def update_route(route_data):
    """Atualiza uma rota existente, adicionando ou reordenando pedidos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    route_id = route_data['id']
    
    try:
        # Atualiza o link do Google Maps
        cursor.execute("UPDATE routes SET google_maps_link = ? WHERE id = ?", (route_data['google_maps_link'], route_id))

        # Deleta as associações antigas para recriar com a nova ordem
        cursor.execute("DELETE FROM route_orders WHERE route_id = ?", (route_id,))
        
        order_ids_to_update = []
        for i, order in enumerate(route_data['orders']):
            order_id = order['id']
            order_ids_to_update.append(order_id)
            cursor.execute(
                "INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES (?, ?, ?)",
                (route_id, order_id, i + 1)
            )

        # Garante que todos os pedidos na rota estão com status 'routed'
        placeholders = ', '.join('?' for _ in order_ids_to_update)
        cursor.execute(
            f"UPDATE orders SET status = 'routed' WHERE id IN ({placeholders})",
            order_ids_to_update
        )
        conn.commit()
    finally:
        conn.close()

def get_all_created_routes():
    """Busca todas as rotas criadas e os pedidos associados a elas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            r.id as route_id, 
            r.google_maps_link, 
            r.status as route_status,
            ro.order_id,
            ro.delivery_sequence
        FROM routes r
        JOIN route_orders ro ON r.id = ro.route_id
        ORDER BY r.id, ro.delivery_sequence
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    routes = {}
    for row in rows:
        route_id = row['route_id']
        if route_id not in routes:
            routes[route_id] = {
                'id': route_id,
                'status': row['route_status'],
                'google_maps_link': row['google_maps_link'],
                'orders': []
            }
        routes[route_id]['orders'].append({
            'id': row['order_id'],
            'sequence': row['delivery_sequence']
        })
        
    return list(routes.values())

# Executa a configuração inicial quando este módulo é importado
setup_database()

