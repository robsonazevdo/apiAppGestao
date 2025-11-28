from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from consulta import delete_stock, fetch_all_stock, fetch_all_stock_movements, get_stock_by_id, insert_stock, update_stock



stock = Blueprint('stock', __name__, url_prefix='/stock')




@stock.route('/all', methods=['GET'])
def get_all_stock():
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


    
    return fetch_all_stock()



@stock.route('/movimentacoes', methods=['POST'])
def get_all_stock_movements():
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
    return fetch_all_stock_movements(name)



@stock.route('/update', methods=['PUT'])  
def update_stock():
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

    return update_stock(id, product_id, type, quantity, description, datetime,)



@stock.route('/delete/<int:stock_id>', methods=['DELETE'])  
def delete_stock_route(stock_id):
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

    stock = get_stock_by_id(stock_id)
    if not stock:
        return jsonify({"error": "Produto não encontrado"}), 404

    success, message = delete_stock(stock_id)
    if not success:
        return jsonify({"error": "Erro ao deletar Produto", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200



@stock.route('/stock', methods=['POST'])
def create_stock_route():
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

    return insert_stock(product_id, quantity, movement_type, movement_description, movement_date)

     


