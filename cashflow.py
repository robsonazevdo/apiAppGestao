from flask import Blueprint, jsonify
import sqlite3
from datetime import datetime
from flask import request

from database import get_db

cashflow = Blueprint("cashflow", __name__)

def get_conn():
    return sqlite3.connect("database.db", check_same_thread=False)

@cashflow.route("/cashflow/daily", methods=["GET"])
def fluxo_diario():
    conn = get_conn()
    cursor = conn.cursor()

    hoje = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT id, description, amount, type
        FROM cashflow
        WHERE DATE(datetime) = ?
        ORDER BY datetime DESC
    """, (hoje,))

    rows = cursor.fetchall()

    entradas = sum(r[2] for r in rows if r[3] == "entrada")
    saidas = sum(r[2] for r in rows if r[3] == "saida")

    transacoes = [
        {
            "id": r[0],
            "descricao": r[1],
            "valor": r[2],
            "tipo": r[3]
        }
        for r in rows
    ]

    return jsonify({
        "entradas": entradas,
        "saidas": saidas,
        "transacoes": transacoes
    })


@cashflow.route("/cashflow/monthly", methods=["GET"])
def fluxo_mensal():
    conn = get_conn()
    cursor = conn.cursor()

    # Recebe ?month=2025-11
    mes = request.args.get("month")
    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT 
            strftime('%d', datetime) AS dia,
            IFNULL(SUM(CASE WHEN type = 'entrada' THEN amount END), 0) AS entradas,
            IFNULL(SUM(CASE WHEN type = 'saida' THEN amount END), 0) AS saídas,
            IFNULL(SUM(CASE WHEN type = 'entrada' THEN amount
                            ELSE -amount END), 0) AS liquido
        FROM cashflow
        WHERE strftime('%Y-%m', datetime) = ?
        GROUP BY dia
        ORDER BY dia
    """, (mes,))

    dias = []
    total_entradas = 0
    total_saidas = 0
    total_liquido = 0

    for row in cursor.fetchall():
        dia = row[0]
        entradas = float(row[1] or 0)
        saidas = float(row[2] or 0)
        liquido = float(row[3] or 0)

        dias.append({
            "dia": dia,
            "entradas": entradas,
            "saidas": saidas,
            "liquido": liquido
        })

        total_entradas += entradas
        total_saidas += saidas
        total_liquido += liquido

    return jsonify({
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "total_liquido": total_liquido,
        "dias": dias
    })



@cashflow.route("/cashflow/add", methods=["POST"])
def add_cashflow():
    data = request.json
    descricao = data.get("descricao")
    valor = float(data.get("valor"))
    tipo = data.get("tipo")  
    date = data.get("date")

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cashflow (type, description, amount, datetime)
        VALUES (?, ?, ?, ?)
    """, (tipo, descricao, valor, date))

    conn.commit()
    conn.close()

    return jsonify({"message": "Lançamento salvo com sucesso!"})


@cashflow.route("/weekly", methods=["GET"])
def fluxo_semanal():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            strftime('%w', created_at) AS weekday,
            SUM(value) as total
        FROM cashflow
        WHERE DATE(created_at) >= DATE('now', '-6 days')
        GROUP BY weekday
        ORDER BY weekday
    """)

    rows = cursor.fetchall()

    dias = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

    resultado = [
        {
            "week_day": dias[int(row["weekday"])],
            "total": row["total"]
        }
        for row in rows
    ]

    return jsonify(resultado)


@cashflow.route("/payment-method", methods=["GET"])
def fluxo_pagamento():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT payment_method, SUM(value) as total
        FROM cashflow
        GROUP BY payment_method
    """)

    rows = cursor.fetchall()
    return jsonify([dict(row) for row in rows])


@cashflow.route("/cashflow/report", methods=["GET"])
def relatorio_financeiro():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN type='entrada' THEN amount ELSE 0 END),
            SUM(CASE WHEN type='saida' THEN amount ELSE 0 END)
        FROM cashflow
    """)

    entradas, saidas = cursor.fetchone()
    entradas = entradas or 0
    saidas = saidas or 0

    saldo = entradas - saidas

    return jsonify({
        "entradas": entradas,
        "saídas": saidas,
        "saldo": saldo
    })
