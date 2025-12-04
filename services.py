from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from consulta import create_barber_service, delete_service, fetch_all_services, fetch_search_service, get_service_by_id, insert_service, search_service_with_barber, update_service



service = Blueprint('service', __name__, url_prefix='/service')




@service.route('/all', methods=['GET'])
def get_all_service():
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


    
    return fetch_all_services()


@service.route('/service', methods=['POST'])  
def create_service_route():
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
    if not data or "name" not in data:
        return jsonify({ "error": "Campos obrigatórios não preenchidos" }), 400

    name = data["name"]
    return insert_service(name)




@service.route('/name', methods=['POST'])  
def get_search_service():
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

    return fetch_search_service(name)

@service.route('/update', methods=['PUT'])  
def update_services():
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
    

    if not name:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400

    return update_service(id, name)


@service.route('/delete/<int:service_id>', methods=['DELETE'])  
def delete_service_route(service_id):
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

    service = get_service_by_id(service_id)
    if not service:
        return jsonify({"error": "Serviço não encontrado"}), 404

    success, message = delete_service(service_id)
    if not success:
        return jsonify({"error": "Erro ao deletar service", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200



@service.route('/barber_service', methods=['POST'])
def add_barber_service():
    data = request.get_json()
    barber_id = data.get("barber_id")
    service_id = data.get("service_id")
    price = data.get("price")
    duration = data.get("duration")

    if not all([barber_id, service_id, price, duration]):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    return create_barber_service(barber_id, service_id, price, duration)



@service.route('/barber_service/name', methods=['POST'])  
def get_search_service_name():
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
    print(data)
    name = data.get("name")

    if not name:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400

    return search_service_with_barber(name)

