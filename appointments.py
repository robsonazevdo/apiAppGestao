from flask import Blueprint, request, jsonify
from utils import verify_token
from users import get_user
from consulta import create_appointments, delete_appointment_by_id, get_appointments_by_user, get_appointment_by_id, get_today_summary

appointments = Blueprint('appointments', __name__)



@appointments.route('/appointments', methods=['POST'])
def create_appointment():
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

    data = request.get_json()
    client_id = data.get("client_id")
    barber_id = data.get("barber_id")
    service_id = data.get("service_id")
    datetime_value = data.get("datetime")

    # Verifica campos obrigatórios
    if not all([client_id, barber_id, service_id, datetime_value, user['email']]):
        return jsonify({"error": "Dados incompletos"}), 400

    # Chama a função principal de criação
    return create_appointments(
        client_id,
        barber_id,
        service_id,
        datetime_value,
        user['email']
    )

    


@appointments.route('/appointments', methods=['GET'])
def list_appointments():
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

    try:
        appointments = get_appointments_by_user(user["email"])
        return jsonify({
            "error": "",
            "appointments": appointments  # <- mesmo que vazio, é sucesso
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Erro ao buscar agendamentos",
            "details": str(e)
        }), 500



@appointments.route('/appointments/<int:appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
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
   
    appointment = get_appointment_by_id(appointment_id)
    if not appointment:
        return jsonify({"error": "Agendamento não encontrado"}), 404

    if appointment["user_email"] != user["email"]:
        return jsonify({"error": "Permissão negada"}), 403

    success, message = delete_appointment_by_id(appointment_id)
    if not success:
        return jsonify({"error": "Erro ao deletar agendamento", "details": message}), 500

    return jsonify({"success": True, "message": message}), 200


@appointments.route("/appointments/today-summary", methods=["GET"])
def today_summary():
    summary = get_today_summary()
    
    return jsonify({"summary": summary})



