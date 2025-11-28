from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from consulta import delete_products, fetch_all_products, fetch_search_products, get_products_by_id, insert_products, update_products



products = Blueprint('products', __name__, url_prefix='/products')




@products.route('/all', methods=['GET'])
def get_all_products():
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


    
    return fetch_all_products()


@products.route('/products', methods=['POST'])  
def create_products_route():
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
    price = data["price"]
    cost = data["cost"]
    unit = data["unit"]
    description = data["description"]
    
    return insert_products(name, price, cost, unit, description)




@products.route('/name', methods=['POST'])  
def get_search_products():
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

    return fetch_search_products(name)



@products.route('/update', methods=['PUT'])  
def update_product():
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
    price = data.get("price")
    cost = data.get("cost")
    unit = data.get("unit")
    description = data.get("description")
    
  
    if not name:
        return jsonify({ "error": "Nome não fornecido", "data": [] }), 400

    return update_products(id, name, price, cost, unit, description)


@products.route('/delete/<int:products_id>', methods=['DELETE'])  
def delete_products_route(products_id):
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

    products = get_products_by_id(products_id)
    if not products:
        return jsonify({"error": "Produto não encontrado"}), 404

    success, message = delete_products(products_id)
    if not success:
        return jsonify({"error": "Erro ao deletar Produto", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200


@products.route('/list', methods=['GET'])
def list_products():
    return fetch_all_products()

