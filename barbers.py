from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from datetime import datetime, timedelta
import sqlite3
from consulta import fetch_all_barbers, get_availability_for_date, get_full_barber, add_availability_for_date


barbers = Blueprint('barbers', __name__)
barber = Blueprint('barber', __name__, url_prefix='/barber')




@barbers.route('/barbers/all', methods=['GET'])
def get_all_barbers():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado", "data": [] }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado", "data": [] }), 404


    
    return fetch_all_barbers()




@barbers.route('/barbers/search', methods=['GET'])
def search_barbers():
    token = request.args.get('token')
    name_query = request.args.get('name', '').strip().lower()

    if not token:
        return jsonify({ "error": "Token não fornecido", "data": [] }), 401

    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado", "data": [] }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado", "data": [] }), 404

    # Consulta ao banco filtrando por nome
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    search_pattern = f"%{name_query}%"
    cur.execute("SELECT * FROM barbers WHERE LOWER(name) LIKE ?", (search_pattern,))
    barbers = cur.fetchall()
    
    data = [dict(row) for row in barbers]

    conn.close()  # ✅ importante

    return jsonify({
        "error": "",
        "data": data
    })





@barbers.route('/barbers', methods=['GET'])
def get_barbers():
    token = request.args.get('token')
    loc = request.args.get('loc')

    if not token:
        return jsonify({ "error": "Token não fornecido", "loc": "", "data": [] }), 401

    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado", "loc": "", "data": [] }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado", "loc": "", "data": [] }), 404

    if not loc:
        return jsonify({
            "error": "",
            "loc": "",
            "data": []
        })

    # Consulta ao banco filtrando pela localização
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM barbers WHERE LOWER(loc) = LOWER(?)", (loc,))
    barbers = cur.fetchall()

    data = [dict(barber) for barber in barbers]

    return jsonify({
        "error": "",
        "loc": loc,
        "data": data
    })



@barber.route('/<int:barber_id>', methods=['GET'])
def get_barber(barber_id):
    # Pega o cabeçalho Authorization
    auth_header = request.headers.get('Authorization')

    # Verifica se existe e começa com "Bearer "
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "error": "Token não fornecido" }), 401

    # Extrai o token do cabeçalho
    token = auth_header.split(" ")[1]

    # Valida o token
    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado" }), 401

    # Busca o barbeiro
    barber = get_full_barber(barber_id)

    if not barber:
        return jsonify({ "error": "Barbeiro não encontrado" }), 404

    # Retorna os dados do barbeiro
    return jsonify({
        "error": "",
        "data": barber
    })


def get_barber_by_id(barber_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM barbers WHERE id = ?", (barber_id,))
    row = cur.fetchone()

    return dict(row) if row else None


@barber.route("/barber/<int:barber_id>/availability")
def barber_availability(barber_id):
    date = request.args.get("date")
    if not date:
        return jsonify({"error":"date param required"}), 400
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
   
   
    cur.execute("""
      SELECT ah.id as hour_id, ah.hour, ah.is_booked, a.id as availability_id
      FROM availability a
      JOIN availability_hours ah ON ah.availability_id = a.id
      WHERE a.barber_id = ? AND a.date = ?
      ORDER BY ah.hour
    """, (barber_id, date))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"hours": rows})


@barber.route("/barbers/<int:barber_id>/availability", methods=["POST"])
def add_availability_endpoint(barber_id):
    data = request.get_json()

    date = data.get("date")           # "2025-06-02"
    slots = data.get("slots", [])     # ["09:00", "09:30"]

    if not date or not slots:
        return {"error": "Envie 'date' e 'slots'."}, 400

    return add_availability_for_date(barber_id, date, slots)


@barber.route("/availability/all", methods=["GET"])
def get_all_availability():
    date = request.args.get("date")
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    barbers = cur.execute("SELECT id, name FROM barbers").fetchall()

    result = []
    for b in barbers:
        av = get_availability_for_date(b["id"], date)
        result.append(av)

    return result


@barber.route("/barbers/<int:barber_id>/availability", methods=["GET"])
def get_availability_endpoint(barber_id):
    date = request.args.get("date")  # YYYY-MM-DD
    return get_availability_for_date(barber_id, date)
