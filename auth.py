from flask import Blueprint, request, jsonify 
from consulta import get_user_by_email
from users import get_user, add_user
from utils import generate_token, verify_token, hash_password, verify_password
import sqlite3

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/user', methods=['POST'])
def register():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if get_user(email):
            return jsonify({ "error": "Usuário já existe" }), 400

        hashed = hash_password(password)
        success, message = add_user(email, name, hashed)
        
        if not success:
            return jsonify({ "error": message }), 500

        token = generate_token({ "email": email })
        return jsonify({ "token": token })

    except Exception as e:
        
        print("Erro ao registrar usuário:", e)
        return jsonify({ "error": "Erro interno", "details": str(e) }), 500





@auth.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = get_user_by_email(email)
    if not user or not verify_password(password, user['password']):
        return jsonify({ "error": "Credenciais inválidas" }), 401

    token = generate_token({ "email": email })
    return jsonify({ 
        "token": token, 
        "data": { 
            "avatar": user.get("avatar", ""), 
            "name": user["name"] 
        } 
    })




@auth.route('/check', methods=['POST'])
def check():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "error": "Token não fornecido" }), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)

    if not decoded:
        return jsonify({ "error": "Token inválido" }), 401

    user = get_user(decoded['email'])
    if not user:
        return jsonify({ "error": "Usuário não encontrado" }), 404

    new_token = generate_token({ "email": decoded['email'] })
    return jsonify({ "token": new_token, "data": { "avatar": user["avatar"], "name": user["name"] } })


@auth.route('/logout', methods=['POST'])
def logout():
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({ "error": "Token não fornecido" }), 400

    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado" }), 401

    
    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado" }), 404

    
    return jsonify({ "error": "" })  


@auth.route('/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({ "error": "Token não fornecido" }), 400

    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado" }), 401

    user = get_user(decoded.get('email'))
    if not user:
        return jsonify({ "error": "Usuário não encontrado" }), 404

    new_token = generate_token({ "email": decoded['email'] })

    return jsonify({
        "token": new_token,
        "data": {
            "name": user["name"],
            "avatar": user["avatar"]
        }
    })



@auth.route('/favorite', methods=['POST'])
def favorite():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "error": "Token ausente ou inválido" }), 401

    token = auth_header.split(" ")[1]

    data = request.get_json()
    barber_id = data.get('barber')

    if not barber_id:
        return jsonify({ "error": "barber_id é obrigatório" }), 400

    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido" }), 401

    user_email = decoded.get("email")

    # Alterna favorito
    from consulta import toggle_favorite
    favorited = toggle_favorite(user_email, barber_id)
    
    return jsonify({ "favorited": favorited }), 200


@auth.route('/favorited', methods=['GET'])
def favorited():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "error": "Token ausente ou inválido" }), 401

    token = auth_header.split(" ")[1]
    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido" }), 401

    user_email = decoded.get("email")
    barber_id = request.args.get('barber')

    if not barber_id:
        return jsonify({ "error": "barber_id é obrigatório" }), 400

    from consulta import is_favorited
    favoritedi = is_favorited(user_email, int(barber_id))

    return jsonify({ "favorited": favoritedi }), 200



@auth.route('/favorites', methods=['GET'])
def get_user_favorites():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({ "error": "Token ausente ou inválido" }), 401

    token = auth_header.split(" ")[1]

    decoded = verify_token(token)
    if not decoded:
        return jsonify({ "error": "Token inválido ou expirado" }), 401

    user_email = decoded.get("email")

    if not user_email:
        return jsonify({
            "error": "",
            "user_email": "",
            "data": []
        })

    from consulta import get_favorites
    favorites = get_favorites(user_email)

    data = [dict(barber) for barber in favorites]

    return jsonify({
            "error": "",
            "user_email": user_email,
            "data": data
        }), 200

    
