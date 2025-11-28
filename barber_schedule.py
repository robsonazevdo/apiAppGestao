from flask import Blueprint, request, jsonify
from datetime import datetime
import sqlite3

schedule = Blueprint('schedule', __name__)

def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)


@schedule.route("/barbers/schedule/save", methods=["POST"])
def save_barber_schedule():
    data = request.get_json()

    barber_id = data.get("barber_id")
    week = data.get("week")

    if not barber_id or not week:
        return jsonify({"error": "Dados incompletos"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()

        # Apaga horários anteriores da semana
        cur.execute("""
            DELETE FROM barber_custom_hours 
            WHERE barber_id = ?
        """, (barber_id,))

        # Insere nova configuração
        for day in week:
            date = day["date"]

            for h in day["hours"]:
                cur.execute("""
                    INSERT INTO barber_custom_hours 
                    (barber_id, date, time, active, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    barber_id,
                    date,
                    h["time"],
                    0 if h["active"] else 1,
                    datetime.now().isoformat()
                ))
        
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Horários salvos com sucesso!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
