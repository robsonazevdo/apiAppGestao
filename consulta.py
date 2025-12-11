import sqlite3
from flask import jsonify
from datetime import datetime as dt, timedelta



def add_user(email, name, hashed_password):
    try:
        avatar = f'https://i.pravatar.cc/150?u={email}'
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO users (email, name, password, avatar)
            VALUES (?, ?, ?, ?)
        ''', (email, name, hashed_password, avatar))

        conn.commit()
        conn.close()
        return True, "Usuário cadastrado com sucesso"
    except sqlite3.IntegrityError:
        return False, "Usuário já existe"
    except Exception as e:
        return False, str(e)

    
def get_user_by_email(email):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None

    

def fetch_all_barbers():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Busca todos os barbeiros
    cursor.execute("SELECT * FROM barbers")
    barber_rows = cursor.fetchall()

    barbers = []

    for barber in barber_rows:
        barber_id = barber["id"]

        # Fotos
        cursor.execute("SELECT url FROM photos WHERE barber_id = ?", (barber_id,))
        photos = [row["url"] for row in cursor.fetchall()]


        # Testemunhos
        cursor.execute("SELECT name, rate, body FROM testimonials WHERE barber_id = ?", (barber_id,))
        testimonials = [dict(row) for row in cursor.fetchall()]

        # Disponibilidade (dias e horas)
        cursor.execute("SELECT id, date FROM availability WHERE barber_id = ?", (barber_id,))
        availability = []
        for avail in cursor.fetchall():
            avail_id = avail["id"]
            cursor.execute("SELECT hour FROM availability_hours WHERE id = ?", (avail_id,))
            hours = [h["hour"] for h in cursor.fetchall()]
            availability.append({
                "date": avail["date"],
                "hours": hours
            })

        # Monta o dicionário final
        barbers.append({
            "id": str(barber["id"]),
            "name": barber["name"],
            "avatar": barber["avatar"],
            "stars": barber["stars"],
            "lat": barber["lat"],
            "lng": barber["lng"],
            "loc": barber["loc"],
            "photos": photos,
            "testimonials": testimonials,
            "available": availability,
            "appointments": []  # futuramente pode ser preenchido
        })

    conn.close()

    return jsonify({"error": "", "data": barbers})



def get_full_barber(barber_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Dados principais
    cur.execute("SELECT * FROM barbers WHERE id = ?", (barber_id,))
    barber = cur.fetchone()
    if not barber:
        return None

    barber_data = dict(barber)

    # Fotos
    cur.execute("SELECT url FROM photos WHERE barber_id = ?", (barber_id,))
    barber_data["photos"] = [row["url"] for row in cur.fetchall()]

    # Serviços
    cur.execute("SELECT name, price FROM services WHERE barber_id = ?", (barber_id,))
    barber_data["services"] = [dict(row) for row in cur.fetchall()]

    # Depoimentos
    cur.execute("SELECT name, rate, body FROM testimonials WHERE barber_id = ?", (barber_id,))
    barber_data["testimonials"] = [dict(row) for row in cur.fetchall()]

    # Disponibilidade (somente horários disponíveis: is_booked = 0)
    cur.execute("SELECT id, date FROM availability WHERE barber_id = ?", (barber_id,))
    availability_rows = cur.fetchall()
    available = []

    for row in availability_rows:
        availability_id = row["id"]
        cur.execute("""
            SELECT hour FROM availability_hours 
            WHERE availability_id = ? AND is_booked = 0
        """, (availability_id,))
        
        hours = [h["hour"] for h in cur.fetchall()]
        
        # Só adiciona a data se houver horários disponíveis
        if hours:
            available.append({
                "date": row["date"],
                "hours": hours
            })

    barber_data["available"] = available

    return barber_data



def create_appointments(client_id, barber_id, service_id, datetime_str, user_email):
    try:
        dq = dt.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            dq = dt.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        except:
            return jsonify({"success": False, "error": "Invalid datetime format"}), 400

    date_only = dq.strftime("%Y-%m-%d")
    time_only = dq.strftime("%H:%M")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1) pega duração do serviço
    cur.execute("""
        SELECT duration FROM barber_services
        WHERE barber_id = ? AND service_id = ?
    """, (barber_id, service_id))

    row = cur.fetchone()
    duration_minutes = int(row["duration"]) if row else 30

    # 2) calcula slots de 30 min
    slot_minutes = 30
    slots_needed = (duration_minutes + slot_minutes - 1) // slot_minutes

    # 3) availability do barbeiro
    cur.execute("""
        SELECT id FROM barber_custom_hours
        WHERE barber_id = ? AND date = ?
    """, (barber_id, date_only))
    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Barbeiro não tem disponibilidade neste dia"}), 400

    availability_id = row["id"]

    # 4) busca horas da disponibilidade
    cur.execute("""
        SELECT id, time, active
        FROM barber_custom_hours
        WHERE barber_id = ?
        AND date = ?
        ORDER BY time
    """, (barber_id, date_only))


    hours = [dict(h) for h in cur.fetchall()]
    index = next((i for i, h in enumerate(hours) if h["time"] == time_only), None)
    
    if index is None:
        conn.close()
        return jsonify({"success": False, "error": "Horário não encontrado nas disponibilidades"}), 400

    # slots suficientes?
    if index + slots_needed > len(hours):
        conn.close()
        return jsonify({"success": False, "error": "Não há slots suficientes neste horário"}), 400

    # verifica se já está reservado
    for i in range(index, index + slots_needed):
        if hours[i]["active"]:
            conn.close()
            return jsonify({"success": False, "error": f"Horário {hours[i]['time']} já reservado"}), 409

    # 5) transação
    try:
        cur.execute("BEGIN")

        cur.execute("""
            INSERT INTO appointments (client_id, barber_id, service_id, datetime, user_email)
            VALUES (?, ?, ?, ?, ?)
        """, (
            client_id,
            barber_id,
            service_id,
            dq.strftime("%Y-%m-%d %H:%M:%S"),  # CORRIGIDO AQUI
            user_email
        ))

        appointment_id = cur.lastrowid

        # marca slots
        for i in range(index, index + slots_needed):
            cur.execute("UPDATE barber_custom_hours SET active = 1 WHERE id = ?", (hours[i]["id"],))

        conn.commit()

        return jsonify({"success": True, "appointment_id": appointment_id})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        conn.close()



def get_appointments_by_user(email):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            a.id,
            a.barber_id,
            c.name,
            s.name,
            a.datetime,
            b.name,
            b.avatar,
            bs.price
        FROM appointments a
        JOIN barbers b ON a.barber_id = b.id
        LEFT JOIN barber_services bs ON bs.barber_id = a.barber_id AND bs.service_id = a.service_id
        LEFT JOIN services s ON s.id = a.service_id
        LEFT JOIN clients c ON c.id = a.client_id
        WHERE a.user_email = ?
        ORDER BY a.datetime DESC
    ''', (email,))
    
    results = cursor.fetchall()
    conn.close()

    appointments = []
    for row in results:
        appointment = {
            "id": row[0],
            "barber_id": row[1],
            "client_name": row[2],  
            "service_id": row[3],
            "datetime": row[4],
            "barber_name": row[5],
            "barber_avatar": row[6],
            "price": row[7] if row[7] is not None else 0.0
        }
        appointments.append(appointment)

    return appointments



def get_appointment_by_id(appointment_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    print(appointment_id)
    cursor.execute('''
        SELECT a.id, a.user_email, a.barber_id, a.service_id, a.datetime
        FROM appointments a
        WHERE a.id = ?
    ''', (appointment_id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "user_email": result[1],
            "barber_id": result[2],
            "service": result[3],
            "datetime": result[4]
        }
    return None


def delete_appointment_by_id(appointment_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Buscar datetime original
        cursor.execute('SELECT barber_id, datetime FROM appointments WHERE id = ?', (appointment_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Agendamento não encontrado"

        barber_id, datetime_value = result
        date_part, time_part = datetime_value.split(" ")

        # Converter HH:MM:SS -> HH:MM
        time_part = dt.strptime(time_part, "%H:%M:%S").strftime("%H:%M")

        # Deletar agendamento
        cursor.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))

        # Liberar horário corretamente
        cursor.execute('''
            UPDATE barber_custom_hours
            SET active = 0
            WHERE barber_id = ?
              AND date = ?
              AND (time = ? OR time = ltrim(?, '0'))
        ''', (barber_id, date_part, time_part, time_part))

        conn.commit()
        conn.close()
        return True, "Agendamento removido com sucesso"

    except Exception as e:
        return False, str(e)




def toggle_favorite(user_email, barber_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Verifica se já existe
    cursor.execute('SELECT id FROM favorites WHERE user_email=? AND barber_id=?', (user_email, barber_id))
    result = cursor.fetchone()

    if result:
        # Já está favoritado: remove
        cursor.execute('DELETE FROM favorites WHERE id=?', (result[0],))
        conn.commit()
        conn.close()
        return False  # desfavoritado
    else:
        # Adiciona como favorito
        cursor.execute('INSERT INTO favorites (user_email, barber_id) VALUES (?, ?)', (user_email, barber_id))
        conn.commit()
        conn.close()
        return True  # favoritado
    


def get_favorites(user_email):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT b.id, b.name, b.avatar, b.stars, b.lat, b.lng, b.loc
            FROM favorites f
            JOIN barbers b ON f.barber_id = b.id
            WHERE f.user_email = ?
        ''', (user_email,))
        results = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "avatar": row[2],
                "stars": row[3],
                "lat": row[4],
                "lng": row[5],
                "loc": row[6]
            }
            for row in results
        ]
    finally:
        conn.close()



def is_favorited(user_email, barber_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM favorites WHERE user_email=? AND barber_id=?', (user_email, barber_id))
    result = cursor.fetchone()
    conn.close()
    return True if result else False


def get_today_summary():
    from datetime import datetime
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute('''
        SELECT a.service_id, a.barber_id
        FROM appointments a
        WHERE DATE(a.datetime) = ?
    ''', (today,))
    
    appointments = cursor.fetchall()
    total_clients = len(appointments)
    total_revenue = 0.0

    for service_id, barber_id in appointments:
        cursor.execute('''
            SELECT price FROM barber_services
            WHERE service_id = ? AND barber_id = ?
        ''', (service_id, barber_id))
        service = cursor.fetchone()
        if service:
            total_revenue += service[0]

    conn.close()
    return [{
        "date": today,
        "total_clients": total_clients,
        "total_revenue": total_revenue
    }]


def fetch_all_clients():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Busca todos os barbeiros
    cursor.execute("SELECT * FROM clients")
    client_rows = cursor.fetchall()

    clients = []

    for client in client_rows:
        client_id = client["id"]

        

        # Monta o dicionário final
        clients.append({
            "id": str(client["id"]),
            "name": client["name"],
            "phone": client["phone"],
            "email": client["email"],
            "created_at": client["created_at"],
          
        })

    conn.close()
    return jsonify({"error": "", "client": clients})


def fetch_search_clients(name):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients WHERE name LIKE ?", (f"%{name}%",))
    clients = cursor.fetchall()
    conn.close()

    client_list = [dict(row) for row in clients]  
    return jsonify({"error": "","data": client_list})



def create_clients(nome, phone, email, created_at):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO clients (name, phone, email, created_at)
                VALUES (?, ?, ?, ?)
            ''', (nome, phone, email, created_at))

            client_id = cursor.lastrowid

        return {
            "success": True,
            "client": {
                "id": client_id,
                "name": nome,
                "phone": phone,
                "email": email,
                "created_at": created_at
            }
        }, 201
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Cliente já existe ou e-mail duplicado"}, 400
    except Exception as e:
        return {"success": False, "error": str(e)}, 500
    

def update_client(id, nome, phone, email, created_at):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE clients
                SET name = ?, phone = ?, email = ?, created_at = ?
                WHERE id = ?
            ''', (nome, phone, email, created_at, id))

            if cursor.rowcount == 0:
                return {"success": False, "error": "Cliente não encontrado"}, 404

        return {
            "success": True,
            "client": {
                "id": id,
                "name": nome,
                "phone": phone,
                "email": email,
                "created_at": created_at
            }
        }, 200
    except sqlite3.IntegrityError:
        return {"success": False, "error": "E-mail ou telefone duplicado"}, 400
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def get_client_by_id(client_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.id, a.name, a.phone, a.email, a.created_at
        FROM clients a
        WHERE a.id = ?
    ''', (client_id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "name": result[1],
            "phone": result[2],
            "created_at": result[3]
        }
    return None


def delete_client_from_db(client_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM clients WHERE id = ?', (client_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Cliente não encontrado"

        cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        conn.commit()
        conn.close()

        return True, "Cliente removido com sucesso"

    except Exception as e:
        return False, str(e)
    

def fetch_all_services():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # <- isso é essencial
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM services")
    services_rows = cursor.fetchall()

    services = []

    for service in services_rows:
        services.append({
            "id": service["id"],
            "name": service["name"],
        })

    conn.close()
    return jsonify({"error": "", "service": services})



def insert_service(name):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO services (name)
                VALUES (?)
            ''', (name,))  # ✅ Note a vírgula aqui

            id = cursor.lastrowid

        return {
            "success": True,
            "service": {
                "id": id,
                "name": name,
            }
        }, 201

    except sqlite3.IntegrityError:
        return {"success": False, "error": "Serviço já existe"}, 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500



def fetch_search_service(name):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM services WHERE name LIKE ?", (f"%{name}%",))
    services = cursor.fetchall()
    conn.close()

    service_list = [dict(row) for row in services]  
    return jsonify({"error": "","data": service_list})


def update_service(id, name):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE services
                SET name = ?
                WHERE id = ?
            ''', (  name, id,))

            if cursor.rowcount == 0:
                return {"success": False, "error": "Cliente não encontrado"}, 404

        return {
            "success": True,
            "service": {
                "id": id,
                "name": name
            }
        }, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500
    

def delete_service(service_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM services WHERE id = ?', (service_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Service não encontrado"

        cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
        conn.commit()
        conn.close()

        return True, "Service removido com sucesso"

    except Exception as e:
        return False, str(e)
    

def get_service_by_id(service_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.id, a.name, a.price, a.duration, a.barber_id
        FROM services a
        WHERE a.id = ?
    ''', (service_id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "name": result[1],
            "pride": result[2],
            "duration": result[3],
            "barber_id": result[4]
        }
    return None


def create_barber_service(barber_id, service_id, price, duration):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO barber_services (barber_id, service_id, price, duration)
                VALUES (?, ?, ?, ?)
            ''', (barber_id, service_id, price, duration))

            new_id = cursor.lastrowid

        return {
            "success": True,
            "barber_service": {
                "id": new_id,
                "barber_id": barber_id,
                "service_id": service_id,
                "price": price,
                "duration": duration
            }
        }, 201
    except Exception as e:
        return {"success": False, "error": str(e)}, 500



def update_barber_service(barber_id, service_id, price, duration):
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE barber_services
                SET price = ?, duration = ?
                WHERE barber_id = ? AND service_id = ?
            ''', (price, duration, barber_id, service_id))

            if cursor.rowcount == 0:
                return {"success": False, "error": "Registro não encontrado"}, 404

        return {"success": True}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def search_service_with_barber(service_name):
    import sqlite3
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            s.name AS service_name,
            b.name AS barber_name,
            bs.price,
            bs.duration
        FROM barber_services bs
        INNER JOIN services s ON bs.service_id = s.id
        INNER JOIN barbers b ON bs.barber_id = b.id
        WHERE s.name LIKE ?
    ''', (f'%{service_name}%',))

    results = cursor.fetchall()
    conn.close()

    services = [dict(row) for row in results]

    return {
        "error": "",
        "results": services
    }


def fetch_all_products():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products_rows = cursor.fetchall()

    products = [
        {
            "id": product["id"],
            "name": product["name"],
            "cost": product["cost"],
            "unit": product["unit"],
            "description": product["description"],
        }
        for product in products_rows
    ]

    conn.close()
    return jsonify({"error": "", "data": products})  # <- aqui define "data"


def fetch_full_services():
    try:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                s.id AS service_id,
                s.name AS service_name,
                bs.id AS barber_service_id,
                bs.barber_id,
                b.name AS barber_name,
                bs.price,
                bs.duration
            FROM services s
            LEFT JOIN barber_services bs ON bs.service_id = s.id
            LEFT JOIN barbers b ON b.id = bs.barber_id
            ORDER BY s.name ASC
        """)

        rows = cursor.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "service_id": r["service_id"],
                "service_name": r["service_name"],
                "barber_service_id": r["barber_service_id"],
                "barber_id": r["barber_id"],
                "barber_name": r["barber_name"],
                "price": r["price"],
                "duration": r["duration"]
            })

        return jsonify({ "success": True, "data": result }), 200

    except Exception as e:
        return jsonify({ "success": False, "error": str(e) }), 500



def insert_products(name, price, cost, unit, description):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO products (name, price, cost, unit, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, price, cost, unit, description,))  

            id = cursor.lastrowid

        return {
            "success": True,
            "products": {
                "id": id,
                "name": name,
                "price": price,
                "cost": cost,
                "unit": unit,
                "description": description
            }
        }, 201

    except sqlite3.IntegrityError:
        return {"success": False, "error": "Serviço já existe"}, 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
    

def fetch_search_products(name):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{name}%",))
    pruducts = cursor.fetchall()
    conn.close()

    pruducts_list = [dict(row) for row in pruducts]  
    return jsonify({"error": "","data": pruducts_list})


def get_products_by_id(products_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, name, price, cost, unit, description
        FROM products 
        WHERE id = ?
    ''', (products_id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": id,
            "name": result[0],
            "price": result[1],
            "cost": result[2],
            "unit": result[3],
            "description": result[3],
        }
    return None


def delete_products(products_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM products WHERE id = ?', (products_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Produto não encontrado"

        cursor.execute('DELETE FROM products WHERE id = ?', (products_id,))
        conn.commit()
        conn.close()

        return True, "Produto removido com sucesso"

    except Exception as e:
        return False, str(e)
    

def update_products(id, name, price, cost, unit, description):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE products
                SET name = ?, price = ?, cost = ?, unit = ?, description = ?
                WHERE id = ?
            ''', (name, price, cost, unit, description, id))

            if cursor.rowcount == 0:
                return {"success": False, "error": "Produto não encontrado"}, 404

        return {
            "success": True,
            "product": {
                "id": id,
                "name": name,
                "price": price,
                "cost": cost,
                "unit": unit,
                "description": description
            }
        }, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def delete_stock(stock_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM stock_control WHERE id = ?', (stock_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Produto não encontrado"

        cursor.execute('DELETE FROM stock_control WHERE id = ?', (stock_id,))
        conn.commit()
        conn.close()

        return True, "Produto removido com sucesso"

    except Exception as e:
        return False, str(e)  
    

def fetch_all_stock():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # <- isso é essencial
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM stock_control")
    stock_control_rows = cursor.fetchall()

    stock_control = []

    for stock in stock_control_rows:
        stock_control.append({
            "id": stock["id"],
            "product_id": stock["product_id"],
            "type": stock["type"],
            "quantity": stock["quantity"],
            "description": stock["description"],
            "datetime": stock["datetime"],
        })

    conn.close()
    return jsonify({"error": "", "stock": stock_control})



def fetch_all_stock_movements(name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    query = '''
        SELECT sc.id, p.name AS product_name, sc.type, sc.quantity, sc.description, sc.datetime
        FROM stock_control sc
        JOIN products p ON sc.product_id = p.id
        WHERE p.name LIKE ?
        ORDER BY sc.datetime DESC
    '''

    name_param = f"%{name}%"
    cursor.execute(query, (name_param,))
    results = cursor.fetchall()
    conn.close()

    stock_list = [
        {
            "id": row[0],
            "product": row[1],
            "type": row[2],
            "quantity": row[3],
            "description": row[4],
            "datetime": row[5]
        }
        for row in results
    ]

    return jsonify({"success": True, "data": stock_list})




def get_stock_by_id(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * 
        FROM stock_control 
        WHERE id = ?
    ''', (id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": id,
            "product_id": result[0],
            "type": result[1],
            "quantity": result[2],
            "description": result[3],
            "datetime": result[4],
            
        }
    return None


def insert_stock(product_id, quantity, movement_type, movement_description, movement_date,):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO stock_control (product_id, type, quantity, description, datetime)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, movement_type, quantity, movement_description, movement_date))
  

            id = cursor.lastrowid

        return {
            "success": True,
            "stock": {
                "id": id,
                "product_id": product_id,
                "type": movement_type,
                "quantity": quantity,
                "description": movement_description,
                "datetime": movement_date,

            }
        }, 201

    except sqlite3.IntegrityError:
        return {"success": False, "error": "Estoque já existe"}, 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


def update_stock(id, product_id, type, quantity, description, datetime,):
    try:
        with sqlite3.connect("database.db", timeout=10) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE stock_control
                SET product_id = ?,type = ?, quantity = ?,  description = ?, datetime = ?
                WHERE id = ?
            ''', (product_id, type, quantity, description, datetime, id))

            if cursor.rowcount == 0:
                return {"success": False, "error": "Produto não encontrado"}, 404

        return {
            "success": True,
            "stock": {
                "id": id,
                "product_id": product_id,
                "type": type,
                "quantity": quantity,
                "description": description,
                "datetime": datetime,

            }
        }, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def delete_package(package_id: int):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Verifica se o pacote existe
        cursor.execute('SELECT id FROM packages WHERE id = ?', (package_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Pacote não encontrado"

        # Remove serviços relacionados primeiro
        cursor.execute('DELETE FROM package_services WHERE package_id = ?', (package_id,))

        # Agora remove o pacote
        cursor.execute('DELETE FROM packages WHERE id = ?', (package_id,))

        conn.commit()
        conn.close()

        return True, "Pacote removido com sucesso"

    except Exception as e:
        return False, str(e)


def get_package_by_id(package_id: int):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Busca os dados do pacote
    cursor.execute('''
        SELECT id, name, price, duration, expiration_date
        FROM packages 
        WHERE id = ?
    ''', (package_id,))
    
    package = cursor.fetchone()

    if not package:
        conn.close()
        return None

    # Busca os serviços relacionados ao pacote
    cursor.execute('''
        SELECT s.id, s.name, s.price, s.duration
        FROM package_services ps
        JOIN services s ON ps.service_id = s.id
        WHERE ps.package_id = ?
    ''', (package_id,))
    
    services = cursor.fetchall()
    conn.close()

    return {
        "id": package[0],
        "name": package[1],
        "price": package[2],
        "duration": package[3],
        "expiration_date": package[4],
        "services": [
            {
                "id": s[0],
                "name": s[1],
                "price": s[2],
                "duration": s[3],
            } for s in services
        ]
    }


def fetch_all_package():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Buscar todos os pacotes
    cursor.execute("SELECT * FROM packages")
    package_rows = cursor.fetchall()

    packages = []
    for pkg in package_rows:
        # Buscar serviços relacionados a cada pacote
        cursor.execute('''
            SELECT s.id, s.name, s.price, s.duration
            FROM package_services ps
            JOIN services s ON ps.service_id = s.id
            WHERE ps.package_id = ?
        ''', (pkg["id"],))
        
        services = cursor.fetchall()

        packages.append({
            "id": pkg["id"],
            "name": pkg["name"],
            "price": pkg["price"],
            "duration": pkg["duration"],
            "expiration_date": pkg["expiration_date"],
            "services": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "price": s["price"],
                    "duration": s["duration"]
                } for s in services
            ]
        })

    conn.close()
    return jsonify({"error": "", "packages": packages})


def fetch_all_package_movements(name):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = '''
        SELECT p.id, p.name, p.price, p.duration, p.expiration_date
        FROM packages p
        WHERE p.name LIKE ?
        ORDER BY p.id DESC
    '''
    name_param = f"%{name}%"
    cursor.execute(query, (name_param,))
    package_rows = cursor.fetchall()

    packages = []
    for pkg in package_rows:
        # Buscar serviços vinculados ao pacote
        cursor.execute('''
            SELECT s.id, s.name, s.price, s.duration
            FROM package_services ps
            JOIN services s ON ps.service_id = s.id
            WHERE ps.package_id = ?
        ''', (pkg["id"],))
        
        services = cursor.fetchall()

        packages.append({
            "id": pkg["id"],
            "name": pkg["name"],
            "price": pkg["price"],
            "duration": pkg["duration"],
            "expiration_date": pkg["expiration_date"],
            "services": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "price": s["price"],
                    "duration": s["duration"]
                } for s in services
            ]
        })

    conn.close()
    return jsonify({"success": True, "data": packages})




def add_availability_for_date(barber_id, date, slots):
    conn = sqlite3.connect("database.db", timeout=10, check_same_thread=False)
    cur = conn.cursor()

    try:
        # 1) Verifica se já existe disponibilidade
        cur.execute("""
            SELECT id FROM availability 
            WHERE barber_id = ? AND date = ?
        """, (barber_id, date))

        row = cur.fetchone()

        if row:
            availability_id = row[0]
        else:
            cur.execute("""
                INSERT INTO availability (barber_id, date)
                VALUES (?, ?)
            """, (barber_id, date))
            availability_id = cur.lastrowid

        added = 0

        # 2) Insere slots
        for hour in slots:
            cur.execute("""
                INSERT OR IGNORE INTO availability_hours (availability_id, hour, is_booked)
                VALUES (?, ?, 0)
            """, (availability_id, hour))
            added += cur.rowcount

        conn.commit()

        return {
            "success": True,
            "availability_id": availability_id,
            "added_slots": added
        }

    except Exception as e:
        return {"error": str(e)}, 500

    finally:
        conn.close()


def get_availability_for_date(barber_id: int, date_str: str):
    """
    Retorna as horas da disponibilidade para um barbeiro em uma data específica.
    Retorno (python dict):
    {
      "success": True,
      "barber_id": 1,
      "date": "2025-11-23",
      "hours": [
        {"hour_id": 10, "hour": "09:00", "is_booked": 0},
        ...
      ]
    }
    """
    if not date_str:
        return {"success": False, "error": "date required"}, 400

    conn = sqlite3.connect("database.db", timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # Busca availability (id) para barber + date
        cur.execute("""
            SELECT id FROM availability
            WHERE barber_id = ? AND date = ?
        """, (barber_id, date_str))
        row = cur.fetchone()
        if not row:
            # sem disponibilidade criada para essa data
            return {
                "success": True,
                "barber_id": barber_id,
                "date": date_str,
                "hours": []
            }

        availability_id = row["id"]

        # Busca os horários para essa availability
        cur.execute("""
            SELECT id as hour_id, hour, is_booked
            FROM availability_hours
            WHERE availability_id = ?
            ORDER BY hour
        """, (availability_id,))

        hours = [dict(r) for r in cur.fetchall()]

        return {
            "success": True,
            "barber_id": barber_id,
            "date": date_str,
            "hours": hours
        }

    except Exception as e:
        return {"success": False, "error": str(e)}, 500

    finally:
        conn.close()



def generate_week_availability(barber_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    today = dt.now().date()

    # pega horários personalizados do barbeiro
    cur.execute("""
        SELECT weekday, start_time, end_time, slot_minutes
        FROM barber_schedule
        WHERE barber_id = ?
    """, (barber_id,))
    schedule = [dict(s) for s in cur.fetchall()]

    if not schedule:
        conn.close()
        return False, "Barbeiro não tem horários configurados"

    # Gera 7 dias
    for day_offset in range(7):
        date_obj = today + timedelta(days=day_offset)
        date_str = date_obj.strftime("%Y-%m-%d")
        weekday = date_obj.weekday()  # 0=Seg, 6=Dom

        # pega regra do dia
        rule = next((r for r in schedule if r["weekday"] == weekday), None)
        if not rule:
            continue  # barbeiro não trabalha no dia

        # cria availability
        cur.execute("""
            INSERT INTO availability (barber_id, date)
            VALUES (?, ?)
        """, (barber_id, date_str))
        availability_id = cur.lastrowid

        # gera horários baseado na regra
        start = dt.strptime(f"{date_str} {rule['start_time']}", "%Y-%m-%d %H:%M")
        end = dt.strptime(f"{date_str} {rule['end_time']}", "%Y-%m-%d %H:%M")
        slot = int(rule["slot_minutes"])

        h = start
        while h <= end:
            hour_str = h.strftime("%H:%M")
            cur.execute("""
                INSERT INTO availability_hours (availability_id, hour, is_booked)
                VALUES (?, ?, 0)
            """, (availability_id, hour_str))
            h += timedelta(minutes=slot)

    conn.commit()
    conn.close()
    return True, "Disponibilidades da semana geradas"


def fetch_all_orders():
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
    orders.id,
    clients.name,
    orders.status,
    orders.opened_at,
    orders.order_number
FROM orders 
JOIN clients ON clients.id = orders.client_id
WHERE orders.status = 'aberta'
ORDER BY orders.id;

        """)

        rows = cursor.fetchall()
        conn.close()

        data = [
            {
                "id": r[0],
                "cliente": r[1],
                "status": r[2],
                "aberta_em": r[3],
                "order_number": r[4]
            }
            for r in rows
        ]

        return jsonify({
            "error": "",
            "data": data
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Erro ao buscar comandas",
            "data": [],
            "details": str(e)
        }), 500


def delete_order_by_id(id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Buscar datetime original
        cursor.execute('SELECT id, client_id, barber_id, status, order_number FROM orders WHERE id = ?', (id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Comanda não encontrado"

        
        # Deletar comanda
        cursor.execute('DELETE FROM orders WHERE id = ?', (id,))


        conn.commit()
        conn.close()
        return True, "Comanda cancelada com sucesso"

    except Exception as e:
        return False, str(e)



def get_order_by_id(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, client_id, barber_id, opened_at, status, order_number FROM orders
            WHERE id = ?
    ''', (id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "client_id": result[1],
            "barber_id": result[2],
            "opened_at": result[3],
            "status": result[4],
            "order_number": result[5]
        }
    return None


def item_order_by_id(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, price
        FROM items
        WHERE id = ?
    ''', (id,))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "name": result[1],
            "price": result[2],
        }
    return None


def insert_item_ordrs(order_id, item_id, name, qtd, price, total):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO orders_items (order_id, item_id, name, qtd, price, total)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, item_id, item["name"], qtd, price, total))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "name": result[1],
            "price": result[2],
        }
    return None 


def delete_order_item_by_id(id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Buscar datetime original
        cursor.execute('SELECT id, order_id, service_id, price, qtd FROM order_items WHERE id = ?', (id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "Item não encontrado"

        
        # Deletar comanda
        cursor.execute('DELETE FROM order_items WHERE id = ?', (id,))


        conn.commit()
        conn.close()
        return True, "Item removido com sucesso"

    except Exception as e:
        return False, str(e)

