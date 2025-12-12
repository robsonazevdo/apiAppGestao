import datetime
from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
import sqlite3
from consulta import delete_order_item_by_id, fetch_all_orders, delete_order_by_id, get_order_by_id
from database import get_db, close_connection

orders = Blueprint("orders", __name__, url_prefix="/orders")



@orders.route("/create", methods=["POST"])
def create_order():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token não fornecido"}), 401

        token = auth_header.split(" ")[1]
        decoded = verify_token(token)
        if not decoded:
            return jsonify({"error": "Token inválido"}), 401

        user = get_user(decoded.get("email"))
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        opened_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        data = request.get_json()
        order_number = data.get("order_number")
        client_id = data.get("client_id")
        barber_id = data.get("barber_id")

        if not order_number:
            return jsonify({"error": "order_number é obrigatório"}), 400
        if not client_id:
            return jsonify({"error": "client_id é obrigatório"}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status FROM orders
            WHERE order_number = ?
            ORDER BY opened_at DESC
            LIMIT 1
        """, (order_number,))
        last = cursor.fetchone()

        if last and last["status"] == "aberta":
            return jsonify({"error": "Comanda já está aberta"}), 409

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (
                client_id,
                barber_id,
                opened_at,
                order_number,
                status
            )
            VALUES (?, ?, ?, ?, 'aberta')
        """, (client_id, barber_id, opened_at, order_number))

        conn.commit()
        order_id = cursor.lastrowid
        cursor.close()


        return jsonify({
            "message": "Comanda criada com sucesso",
            "order_id": order_id 
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erro ao criar comanda", "details": str(e)}), 500

    


@orders.route("/<int:id>/items", methods=["GET"])
def list_items(id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 
            oi.id AS item_id,
            oi.qtd,
            oi.price AS item_price,
            (oi.qtd * oi.price) AS subtotal,

            s.id AS service_id,
            s.name AS service_name,

            COALESCE(bs.price, 0) AS barber_price,
            COALESCE(bs.duration, 0) AS duration,

            b.id AS barber_id,
            b.name AS barber_name,

            o.total AS item_total,
            o.id AS order_id

        FROM order_items oi
        JOIN services s ON s.id = oi.service_id
        JOIN orders o ON o.id = oi.order_id
        LEFT JOIN barber_services bs 
            ON bs.service_id = s.id 
        AND bs.barber_id = o.barber_id
        LEFT JOIN barbers b ON b.id = o.barber_id

        WHERE oi.order_id = ?;
        """, (id,))
        
        rows = cursor.fetchall()

        cursor.execute("SELECT total, status FROM orders WHERE id = ?", (id,))
        data = cursor.fetchone()

        conn.close()

        if not data:
            return jsonify({"error": "Comanda não encontrada"}), 404

        total, status = data

        items = [
            {
                "item_id": r[0],
                "qtd": r[1],
                "item_price": r[2],
                "subtotal": r[3],

                "service_id": r[4],
                "service_name": r[5],

                "barber_price": r[6],
                "duration": r[7],

                "barber_id": r[8],
                "barber_name": r[9],

                "order_id": r[11]  # 👈 ADICIONADO AQUI
            }
            for r in rows
        ]

        return jsonify({
            "items": items,
            "total": total,
            "status": status,
        })

    except Exception as e:
        return jsonify({
            "error": "Erro ao buscar itens", 
            "details": str(e)
        }), 500



# =========================================
# 🔹 Listar todas as comandas
# =========================================
@orders.route('/all', methods=['GET'])
def get_all_orders():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido", "data": []}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido", "data": []}), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({"error": "Usuário não encontrado", "data": []}), 404

    return fetch_all_orders()



# =========================================
# 🔹 Cancelar/deletar comanda
# =========================================
@orders.route('/<int:id>/cancel', methods=['DELETE'])
def cancel_orders(id):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido"}), 401

    user = get_user(decoded["email"])
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    orders = get_order_by_id(id)
    if not orders:
        return jsonify({"error": "Comanda não encontrada"}), 404

    success, message = delete_order_by_id(id)
    if not success:
        return jsonify({"error": "Erro ao deletar comanda", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200



@orders.route("/<int:order_id>/items/<int:item_id>", methods=["DELETE"])
def delete_item(order_id, item_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        
        # CORRETO: id = item_id, order_id = order_id
        cursor.execute("""
            DELETE FROM order_items 
            WHERE id = ? AND order_id = ?
        """, (item_id, order_id))

        # Recalcula o total corretamente
        cursor.execute("""
            UPDATE orders
            SET total = (
                SELECT COALESCE(SUM(qtd * price), 0) 
                FROM order_items 
                WHERE order_id = ?
            )
            WHERE id = ?
        """, (order_id, order_id))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Item removido"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Erro ao remover item", 
            "details": str(e)
        }), 500




# =========================================
# 🔹 Finalizar comanda
# =========================================
@orders.route("/number/<order_number>/finalizar", methods=["POST"])
def finalizar_order(order_number):
    try:
        data = request.get_json()
        forma_pagamento = data.get("forma_pagamento")
        desconto = float(data.get("desconto") or 0)

        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT id, barber_id, status
            FROM orders
            WHERE order_number = ? AND status = 'aberta'
            ORDER BY opened_at DESC
            LIMIT 1
        """, (order_number,))
        
        order = cur.fetchone()

        if not order:
            return jsonify({"error": "Nenhuma comanda aberta com este número"}), 400

        order_id = order["id"]
        barber_id = order["barber_id"]

        cur.execute("SELECT price, qtd FROM order_items WHERE order_id = ?", (order_id,))
        itens = cur.fetchall()

        total = sum(float(i["price"]) * int(i["qtd"]) for i in itens)
        total_final = max(0, total - desconto)

        # 🔥 ATUALIZAR COMANDA
        cur.execute("""
            UPDATE orders
            SET 
                status = 'finalizada',
                total = ?,
                discount = ?,
                total_final = ?,
                payment_method = ?
            WHERE id = ? AND status = 'aberta'
        """, (total, desconto, total_final, forma_pagamento, order_id))

        if cur.rowcount == 0:
            return jsonify({"error": "Comanda já está finalizada ou cancelada"}), 400

        # 🔥 INSERIR NO FLUXO DE CAIXA (CORRETO)
        cur.execute("""
            INSERT INTO cashflow (barber_id, type, description, amount, payment_method, datetime)
            VALUES (?, 'entrada', ?, ?, ?, datetime('now'))
        """, (
            barber_id,
            f"Comanda {order_number} finalizada",
            total_final,
            forma_pagamento
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "order_id": order_id,
            "order_number": order_number,
            "barber_id": barber_id,
            "total_original": total,
            "desconto": desconto,
            "total_final": total_final,
            "forma_pagamento": forma_pagamento,
            "fluxo_registrado": True,
            "status": "finalizada"
        }), 200

    except Exception as e:
        print("Erro ao finalizar:", e)
        return jsonify({"error": "Erro no servidor", "details": str(e)}), 500



# =========================================
# 🔹 Buscar comanda completa
# =========================================
@orders.route("/<int:order_id>", methods=["GET"])
def get_order(order_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.id, o.order_number, o.total, o.status, c.name
            FROM orders o
            JOIN clients c ON c.id = o.client_id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            return jsonify({"error": "Comanda não encontrada"}), 404

        cursor.execute("""
            SELECT id, item_name, quantity, price, total
            FROM order_items
            WHERE order_id = ?
        """, (order_id,))
        items = cursor.fetchall()

        conn.close()

        return jsonify({
            "order": {
                "id": order[0],
                "order_number": order[1],
                "total": order[2],
                "status": order[3],
                "client": order[4]
            },
            "items": [
                {
                    "id": i[0],
                    "item_name": i[1],
                    "quantity": i[2],
                    "price": i[3],
                    "total": i[4]
                }
                for i in items
            ]
        })

    except Exception as e:
        return jsonify({"error": "Erro ao buscar comanda", "details": str(e)}), 500


@orders.route("/item", methods=["POST"])
def add_order_item():
    # --- Autenticação ---
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido"}), 401

    user = get_user(decoded["email"])
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    # --- Dados recebidos ---
    data = request.get_json()
    order_id = data.get("comanda_id")
    service_id = data.get("service_id")
    client_id = data.get("client_id")
    barber_id = data.get("barber_id")
    qtd = int(data.get("qtd", 1))
    
    
    
    if not order_id or not service_id or not barber_id:
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # --- Buscar preço do serviço (tabela barber_services) ---
        cursor.execute("""
            SELECT price 
            FROM barber_services
            WHERE barber_id = ? AND service_id = ?
        """, (barber_id, service_id))

        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Serviço não encontrado para este barbeiro"}), 404

        price = float(row[0])
        total_item = price * qtd

        # --- Inserir item ---
        cursor.execute("""
            INSERT INTO order_items (order_id, service_id, qtd, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, service_id, qtd, price))

        # --- Atualizar total da comanda ---
        cursor.execute("""
            UPDATE orders
            SET total = (
                SELECT SUM(qtd * price)
                FROM order_items
                WHERE order_id = ?
            )
            WHERE id = ?
        """, (order_id, order_id))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Item adicionado com sucesso",
            "item_total": total_item,
            "price_unitario": price
        }), 201

    except Exception as e:
        return jsonify({"error": "Erro ao adicionar item", "details": str(e)}), 500


@orders.route("/number/<order_number>", methods=["GET"])
def get_order_by_number(order_number):
    try:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row  # permite acessar por nome
        cur = conn.cursor()

        # Buscar comanda + nome do cliente
        cur.execute("""
            SELECT 
                o.id,
                o.order_number,
                c.name AS client_name
            FROM orders o
            JOIN clients c ON c.id = o.client_id
            WHERE o.order_number = ? 
              AND o.status = 'aberta'
        """, (order_number,))

        order = cur.fetchone()

        if not order:
            return jsonify({"error": "Comanda não encontrada ou já finalizada"}), 400

        order_id = order["id"]

        # Buscar itens da comanda
        cur.execute("""
            SELECT 
                oi.id AS item_id,
                s.name AS service_name,
                oi.price AS item_price,
                oi.qtd AS qtd
            FROM order_items oi
            JOIN barber_services bs ON bs.id = oi.service_id
            JOIN services s ON s.id = bs.service_id
            WHERE oi.order_id = ?
        """, (order_id,))

        items_db = cur.fetchall()

        items = []
        total = 0

        for item in items_db:
            item_price = float(item["item_price"])
            qtd = item["qtd"]

            items.append({
                "item_id": item["item_id"],
                "service_name": item["service_name"],
                "item_price": item_price,
                "qtd": qtd
            })

            total += item_price * qtd

        return jsonify({
            "order_number": order["order_number"],
            "client_name": order["client_name"],
            "items": items,
            "total": total
        })

    except Exception as e:
        print("Erro:", e)
        return jsonify({"error": "Erro no servidor"}), 500
