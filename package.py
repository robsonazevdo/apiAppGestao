from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from consulta import delete_package, get_package_by_id, fetch_all_package, fetch_all_package_movements #insert_package, update_package



package = Blueprint('package', __name__, url_prefix='/package')




@package.route('/all', methods=['GET'])
def get_all_package():
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


    
    return fetch_all_package()



@package.route('/movimentacoes', methods=['POST'])
def get_all_package_movements():
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

    data = request.get_json()
    name = data.get("name")
    
    # Puxa os dados do banco
    return fetch_all_package_movements(name)



@package.route('/update', methods=['PUT'])  
def update_package():
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
    product_id = data.get(" product_id")
    type = data.get("type")
    quantity = data.get("quantity")
    datetime = data.get("datetime")
    description = data.get("description")
    
  
    if not id:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400

    return update_package(id, product_id, type, quantity, description, datetime,)



@package.route('/delete/<int:package_id>', methods=['DELETE'])  
def delete_package_route(package_id):
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

    package = get_package_by_id(package_id)
    if not package:
        return jsonify({"error": "Produto não encontrado"}), 404

    success, message = delete_package(package_id)
    if not success:
        return jsonify({"error": "Erro ao deletar Produto", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200



@package.route('/package', methods=['POST'])
def create_package_route():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token não fornecido"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Token inválido ou expirado"}), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    movement_type = data.get('type')  # "entrada" ou "saida"
    movement_description = data.get('description')
    movement_date = data.get('date')  # Ex: "2025-07-17"
    print(product_id, quantity, movement_type, movement_description, movement_date)
    if not all([product_id, quantity, movement_type, movement_description, movement_date]):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    return insert_package(product_id, quantity, movement_type, movement_description, movement_date)

     


