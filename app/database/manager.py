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
    """Cria as tabelas e atualiza estrutura se necessário."""
    print("Verificando e configurando o banco de dados...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    is_postgres = isinstance(conn, psycopg2.extensions.connection)
    
    autoincrement_syntax = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    text_syntax = "VARCHAR(255)" if is_postgres else "TEXT"
    
    # 1. Tabelas Básicas
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS orders (
        id {text_syntax} PRIMARY KEY,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        status {text_syntax} NOT NULL DEFAULT 'pending'
    )
    ''')
    
    # Adicionamos motoboy_id na tabela routes
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS routes (
        id {autoincrement_syntax},
        google_maps_link TEXT,
        status {text_syntax} NOT NULL DEFAULT 'created',
        motoboy_id INTEGER, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS motoboys (
        id {autoincrement_syntax},
        name {text_syntax} NOT NULL,
        phone {text_syntax},
        status {text_syntax} NOT NULL DEFAULT 'unavailable'
    )
    ''')

    # --- MIGRAÇÃO MANUAL (GAMBIARRA SEGURA) ---
    # Se a tabela routes já existia sem motoboy_id, precisamos adicionar a coluna.
    try:
        if is_postgres:
            cursor.execute("ALTER TABLE routes ADD COLUMN IF NOT EXISTS motoboy_id INTEGER")
        else:
            # SQLite não tem "IF NOT EXISTS" no ADD COLUMN, então tentamos e ignoramos erro
            try:
                cursor.execute("ALTER TABLE routes ADD COLUMN motoboy_id INTEGER")
            except sqlite3.OperationalError:
                pass # Coluna já existe
    except Exception as e:
        print(f"Aviso na migração: {e}")

    conn.commit()
    cursor.close()
    conn.close()

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
    """Busca TODAS as rotas com os dados do motoboy (JOIN)."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        try:
            # JOIN para pegar o nome do motoboy
            sql_routes = """
                SELECT r.*, m.name as motoboy_name 
                FROM routes r
                LEFT JOIN motoboys m ON r.motoboy_id = m.id
            """
            cursor.execute(sql_routes)
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

def create_motoboy(name):
    """Cria um novo motoboy (Apenas nome e status)."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    # Removemos o 'phone' do INSERT
    sql = f"INSERT INTO motoboys (name, status) VALUES ({placeholder}, 'available')"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (name,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao criar motoboy: {e}")
        return False
    finally:
        conn.close()

def get_all_motoboys():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM motoboys")
        return _rows_to_dicts(cursor, cursor.fetchall())
    finally:
        conn.close()

def assign_route_to_motoboy(route_id, motoboy_id):
    """Vincula uma rota a um motoboy, garantindo que ele saia de outras rotas ativas."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        
        # 1. SEGURANÇA: Remove este motoboy de qualquer outra rota que NÃO esteja concluída.
        # Isso impede que o "João" esteja em duas rotas ativas ao mesmo tempo.
        sql_remove_duplicate = f"UPDATE routes SET motoboy_id = NULL WHERE motoboy_id = {placeholder} AND status != 'completed'"
        cursor.execute(sql_remove_duplicate, (motoboy_id,))

        # 2. Agora sim, atribui à nova rota
        sql_route = f"UPDATE routes SET motoboy_id = {placeholder} WHERE id = {placeholder}"
        cursor.execute(sql_route, (motoboy_id, route_id))
        
        # 3. Atualiza o status do motoboy na tabela de motoboys
        sql_boy = f"UPDATE motoboys SET status = 'delivering' WHERE id = {placeholder}"
        cursor.execute(sql_boy, (motoboy_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erro ao atribuir rota: {e}")
        return False
    finally:
        conn.close()

def get_route_by_id(route_id):
    """Busca uma rota específica pelo ID com seus pedidos."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        # Busca a rota
        sql_route = f"SELECT * FROM routes WHERE id = {placeholder}"
        cursor.execute(sql_route, (route_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        route_obj = dict(row)
        
        # Busca os pedidos
        sql_orders = f'''
            SELECT o.id, o.lat, o.lon, ro.delivery_sequence 
            FROM orders o
            JOIN route_orders ro ON o.id = ro.order_id
            WHERE ro.route_id = {placeholder}
            ORDER BY ro.delivery_sequence
        '''
        cursor.execute(sql_orders, (route_id,))
        orders_rows = _rows_to_dicts(cursor, cursor.fetchall())
        
        route_obj['orders'] = [
            {'id': o['id'], 'sequence': o['delivery_sequence'], 'coords': {'lat': o['lat'], 'lon': o['lon']}} 
            for o in orders_rows
        ]
        return route_obj
    finally:
        conn.close()

def update_motoboy_status(motoboy_id, new_status):
    """Atualiza apenas o status do motoboy (ex: available, delivering)."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        sql = f"UPDATE motoboys SET status = {placeholder} WHERE id = {placeholder}"
        cursor.execute(sql, (new_status, motoboy_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar status do motoboy: {e}")
        return False
    finally:
        conn.close()

def remove_order_from_route(route_id, order_id, new_status='pending'):
    """
    Remove um pedido de uma rota.
    new_status: 'pending' (volta pro processador) ou 'unassigned' (fica no limbo manual).
    """
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        # Deleta a associação
        sql = f"DELETE FROM route_orders WHERE route_id = {placeholder} AND order_id = {placeholder}"
        cursor.execute(sql, (route_id, order_id))
        
        # Atualiza o status do pedido
        # Atenção: Usamos placeholder para o status também para evitar SQL Injection
        sql_order = f"UPDATE orders SET status = {placeholder} WHERE id = {placeholder}"
        cursor.execute(sql_order, (new_status, order_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao remover pedido da rota: {e}")
        return False
    finally:
        conn.close()

def add_order_to_route(route_id, order_id):
    """Adiciona um pedido a uma rota existente (inicialmente no final da fila)."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        # Descobre a última sequência
        sql_seq = f"SELECT MAX(delivery_sequence) FROM route_orders WHERE route_id = {placeholder}"
        cursor.execute(sql_seq, (route_id,))
        max_seq = cursor.fetchone()[0]
        new_seq = 1 if max_seq is None else max_seq + 1
        
        # Cria a associação
        sql = f"INSERT INTO route_orders (route_id, order_id, delivery_sequence) VALUES ({placeholder}, {placeholder}, {placeholder})"
        cursor.execute(sql, (route_id, order_id, new_seq))
        
        # Atualiza status do pedido
        sql_order = f"UPDATE orders SET status = 'routed' WHERE id = {placeholder}"
        cursor.execute(sql_order, (order_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao adicionar pedido na rota: {e}")
        return False
    finally:
        conn.close()

def update_route_status_db(route_id, new_status):
    """Atualiza o status da rota (ex: 'in_progress', 'completed')."""
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        sql = f"UPDATE routes SET status = {placeholder} WHERE id = {placeholder}"
        cursor.execute(sql, (new_status, route_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar status da rota: {e}")
        return False
    finally:
        conn.close()

def unassign_route_from_motoboy(route_id):
    """
    Remove o motoboy da rota e define o status dela como 'created' (Pronto).
    Também libera o motoboy (status 'available').
    """
    conn = get_db_connection()
    placeholder = _get_placeholder(conn)
    try:
        cursor = conn.cursor()
        
        # 1. Descobre quem é o motoboy atual (para liberar ele)
        cursor.execute(f"SELECT motoboy_id FROM routes WHERE id = {placeholder}", (route_id,))
        row = cursor.fetchone()
        motoboy_id = row[0] if row else None
        
        # 2. Atualiza a rota (Remove motoboy e volta para 'created')
        sql_route = f"UPDATE routes SET motoboy_id = NULL, status = 'created' WHERE id = {placeholder}"
        cursor.execute(sql_route, (route_id,))
        
        # 3. Libera o motoboy (se houver um)
        if motoboy_id:
            sql_boy = f"UPDATE motoboys SET status = 'available' WHERE id = {placeholder}"
            cursor.execute(sql_boy, (motoboy_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erro ao desatribuir rota: {e}")
        return False
    finally:
        conn.close()