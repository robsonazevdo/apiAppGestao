from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
import sqlite3
from consulta import fetch_all_orders, delete_order_by_id, get_order_by_id


orders = Blueprint("orders", __name__, url_prefix="/orders")



@orders.route("/create", methods=["POST"])
def create_order():
    # Verificar token
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

    data = request.get_json()

    order_number = data.get("order_number")
    client_id = data.get("client_id")
    barber_id = data.get("barber_id")

    if not order_number:
        return jsonify({"error": "order_number é obrigatório"}), 400
    if not client_id:
        return jsonify({"error": "client_id é obrigatório"}), 400

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Verifica duplicidade
        cursor.execute("SELECT id FROM orders WHERE order_number = ?", (order_number,))
        if cursor.fetchone():
            return jsonify({
                "error": "Comanda já existe",
                "details": "Uma comanda com esse número já está cadastrada"
            }), 409

        cursor.execute("""
            INSERT INTO orders (order_number, client_id, barber_id, status, opened_at)
            VALUES (?, ?, ?, 'aberta', datetime('now'))
        """, (order_number, client_id, barber_id))

        conn.commit()
        order_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "error": "",
            "order_id": order_id,
            "order_number": order_number,
            "status": "aberta",
            "message": "Comanda criada com sucesso"
        }), 201

    except Exception as e:
        return jsonify({"error": "Erro ao criar comanda", "details": str(e)}), 500




@orders.route("/<int:id>/items", methods=["POST"])
def add_items(id):
    # verifica token
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

    data = request.get_json()

    item_name = data.get("item_name")
    quantity = int(data.get("quantity", 1))
    price = float(data.get("price", 0))

    if not item_name or price <= 0:
        return jsonify({"error": "item_name e price são obrigatórios"}), 400

    total_item = price * quantity

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO order_items (order_id, item_name, quantity, price, total)
            VALUES (?, ?, ?, ?, ?)
        """, (id, item_name, quantity, price, total_item))

        cursor.execute("""
            UPDATE orders
            SET total = (SELECT SUM(total) FROM order_items WHERE order_id = ?)
            WHERE id = ?
        """, (id, id))

        conn.commit()
        conn.close()

        return jsonify({"message": "Item adicionado"}), 201

    except Exception as e:
        return jsonify({"error": "Erro ao adicionar item", "details": str(e)}), 500




@orders.route("/<int:id>/items", methods=["GET"])
def list_items(id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, item_name, quantity, price, total
            FROM order_items
            WHERE order_id = ?
        """, (id,))
        rows = cursor.fetchall()

        cursor.execute("SELECT total, status FROM orders WHERE id=?", (id,))
        data = cursor.fetchone()

        conn.close()

        if not data:
            return jsonify({"error": "Comanda não encontrada"}), 404

        total, status = data

        items = [
            {
                "id": r[0],
                "item_name": r[1],
                "quantity": r[2],
                "price": r[3],
                "total": r[4]
            }
            for r in rows
        ]

        return jsonify({
            "items": items,
            "total": total,
            "status": status
        })

    except Exception as e:
        return jsonify({"error": "Erro ao buscar itens", "details": str(e)}), 500



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



# =========================================
# 🔹 Remover item da comanda
# =========================================
@orders.route("/<int:order_id>/items/<int:item_id>", methods=["DELETE"])
def delete_item(order_id, item_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("DELETE FROM order_items WHERE id=? AND order_id=?", (item_id, order_id))

        cursor.execute("""
            UPDATE orders
            SET total = (SELECT COALESCE(SUM(total),0) FROM order_items WHERE order_id = ?)
            WHERE id = ?
        """, (order_id, order_id))

        conn.commit()
        conn.close()

        return jsonify({"message": "Item removido"}), 200

    except Exception as e:
        return jsonify({"error": "Erro ao remover item", "details": str(e)}), 500



# =========================================
# 🔹 Finalizar comanda
# =========================================
@orders.route("/<int:order_id>/finalizar", methods=["POST"])
def close_order(order_id):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM orders WHERE id=?", (order_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Comanda não encontrada"}), 404

        cursor.execute("""
            UPDATE orders
            SET status='finalizada'
            WHERE id=?
        """, (order_id,))

        conn.commit()
        conn.close()

        return jsonify({"message": "Comanda finalizada com sucesso"})

    except Exception as e:
        return jsonify({"error": "Erro ao finalizar comanda", "details": str(e)}), 500



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
