from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from datetime import datetime, timedelta
import sqlite3
from consulta import create_clients, delete_client_from_db, fetch_all_clients, fetch_search_clients, get_client_by_id, update_client



clients = Blueprint('clients', __name__, url_prefix='/clients')



@clients.route('/clients', methods=['POST'])  # <- Use POST se estiver usando JSON no body
def create_cliente():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido ou expirado", "data": [] }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado", "data": [] }), 404

    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email")
    created_at = data.get("created_at")

    if not name:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400
    
    return create_clients(name, phone, email, created_at)



@clients.route('/all', methods=['GET'])
def get_all_cliente():
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


    
    return fetch_all_clients()


@clients.route('/name', methods=['POST'])  # <- Use POST se estiver usando JSON no body
def get_search_cliente():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido ou expirado", "data": [] }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado", "data": [] }), 404

    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400

    return fetch_search_clients(name)


@clients.route('/update', methods=['PUT'])  # <- Use POST se estiver usando JSON no body
def update_cliente():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido ou expirado", "data": [] }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado", "data": [] }), 404

    data = request.get_json()
    id = data.get("id")
    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email")
    created_at = data.get("created_at")

    if not name:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400

    return update_client(id, name, phone, email, created_at)


@clients.route('/delete/<int:client_id>', methods=['DELETE'])  # Corrige rota e nome do parâmetro
def delete_client_route(client_id):
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

    client = get_client_by_id(client_id)
    if not client:
        return jsonify({"error": "Cliente não encontrado"}), 404

    success, message = delete_client_from_db(client_id)
    if not success:
        return jsonify({"error": "Erro ao deletar cliente", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200