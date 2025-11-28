from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
import sqlite3
from consulta import fetch_all_orders



orders = Blueprint("orders", __name__, url_prefix="/orders")




@orders.route("/comandas", methods=["POST"])
def create_comanda():
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
    client_id = data.get("client_id")
    barber_id = data.get("barber_id")

    if not client_id:
        return jsonify({"error": "client_id é obrigatório"}), 400

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO orders (client_id, barber_id, status)
            VALUES (?, ?, 'aberta')
        """, (client_id, barber_id))

        conn.commit()
        order_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "error": "",
            "order_id": order_id,
            "message": "Comanda criada com sucesso"
        })

    except Exception as e:
        return jsonify({"error": "Erro ao criar comanda", "details": str(e)}), 500




@orders.route("/comandas/<int:id>/items", methods=["POST"])
def add_item(id):
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
        return jsonify({"error": "item_name e preço são obrigatórios"}), 400

    total_item = price * quantity

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # inserindo item
        cursor.execute("""
            INSERT INTO order_items (order_id, item_name, quantity, price, total)
            VALUES (?, ?, ?, ?, ?)
        """, (id, item_name, quantity, price, total_item))

        # atualizando total da comanda
        cursor.execute("""
            UPDATE orders 
            SET total = (SELECT SUM(total) FROM order_items WHERE order_id = ?)
            WHERE id = ?
        """, (id, id))

        conn.commit()
        conn.close()

        return jsonify({
            "error": "",
            "message": "Item adicionado",
        })

    except Exception as e:
        return jsonify({"error": "Erro ao adicionar item", "details": str(e)}), 500




@orders.route("/comandas/<int:id>/items", methods=["GET"])
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

        cursor.execute("SELECT total FROM orders WHERE id=?", (id,))
        order_total = cursor.fetchone()[0]

        conn.close()

        items = [
            {
                "id": r[0],
                "item_name": r[1],
                "quantity": r[2],
                "price": r[3],
                "total": r[4],
            }
            for r in rows
        ]

        return jsonify({"error": "", "items": items, "total": order_total})

    except Exception as e:
        return jsonify({"error": "Erro ao buscar itens", "details": str(e)}), 500




@orders.route('/all', methods=['GET'])
def get_all_orders():
    # Verificar token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido", "data": []}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido ou expirado", "data": []}), 401

    # Buscar usuário logado
    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({"error": "Usuário não encontrado", "data": []}), 404

    # Retornar comandas
    return fetch_all_orders()
