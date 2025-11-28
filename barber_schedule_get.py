from flask import Blueprint, request, jsonify
import sqlite3

schedule_get = Blueprint('schedule_get', __name__)

def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)


@schedule_get.route("/barbers/<int:barber_id>/schedule", methods=["GET"])
def get_barber_schedule(barber_id):
    date = request.args.get("date")

    if not date:
        return jsonify({"error": "Parâmetro 'date' obrigatório"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT time, active
            FROM barber_custom_hours
            WHERE barber_id = ? AND date = ?
            ORDER BY time ASC
        """, (barber_id, date))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            # caso ainda não exista configuração retorna vazio (app sabe como tratar)
            return jsonify({
                "success": True,
                "date": date,
                "hours": []
            })

        hours = [
            {"time": r[0], "active": bool(r[1])}
            for r in rows
        ]

        return jsonify({
            "success": True,
            "date": date,
            "hours": hours
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
