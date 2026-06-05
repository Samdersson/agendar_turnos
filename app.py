from flask import Flask, jsonify, render_template, request
import os
import sqlite3
import random
from datetime import date, timedelta
import time

app = Flask(__name__)

def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
    return sqlite3.connect(db_path)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generar", methods=["POST", "GET"])
def generar():

    db = get_db()
    cursor = db.cursor()

    # Restricciones desde frontend
    conflict_pairs = []
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        conflict_pairs = payload.get('conflictPairs', []) or []

    normalized_conflicts = set()
    for pair in conflict_pairs:
        a = (pair.get('a') or '').strip()
        b = (pair.get('b') or '').strip()
        if a and b and a != b:
            normalized_conflicts.add(tuple(sorted([a, b])))

    # limpiar tablas
    cursor.execute("DELETE FROM personas")
    cursor.execute("DELETE FROM turnos")
    cursor.execute("DELETE FROM descansos")
    cursor.execute("DELETE FROM reemplazos")

    # datos base
    titulares = ["Mile", "Eli", "Juli", "May",]
    backup = ["Dai"]

    for p in titulares:
        cursor.execute("INSERT INTO personas (nombre, rol) VALUES (?, 'titular')", (p,))
    for p in backup:
        cursor.execute("INSERT INTO personas (nombre, rol) VALUES (?, 'backup')", (p,))

    db.commit()

    cursor.execute("SELECT id, nombre, rol FROM personas")
    personas = cursor.fetchall()

    titulares_db = [p for p in personas if p[2] == 'titular']
    backup_db = [p for p in personas if p[2] == 'backup'][0]

    inicio = date.today()

    def valida_conflictos(turno_A, turno_B):
        nombres_A = [p[1] for p in turno_A]
        nombres_B = [p[1] for p in turno_B]

        def tiene_conflicto(nombres):
            for i in range(len(nombres)):
                for j in range(i + 1, len(nombres)):
                    par = tuple(sorted([nombres[i], nombres[j]]))
                    if par in normalized_conflicts:
                        return True
            return False

        return not (tiene_conflicto(nombres_A) or tiene_conflicto(nombres_B))

    # 🔹 Generar días laborales
    dias_laborables = [
        inicio + timedelta(days=d)
        for d in range(7)
        if (inicio + timedelta(days=d)).weekday() < 5
    ]

    dias_laborables = sorted(dias_laborables)

    while len(dias_laborables) < 4:
        proximo = dias_laborables[-1] + timedelta(days=1)
        if proximo.weekday() < 5:
            dias_laborables.append(proximo)

    dias_descanso = dias_laborables[:5]

    # ✅ BLOQUE DE DÍAS (configurado desde el front)
    # noDescansoWeekdays: lista de weekday() a los que NO se les puede asignar descanso.
    # 0=Lunes, 1=Martes, ... 4=Viernes
    no_descanso_weekdays = payload.get('noDescansoWeekdays', [0]) or [0]

    # normalizar y asegurar rango esperado
    try:
        no_descanso_weekdays = sorted({int(x) for x in no_descanso_weekdays})
    except Exception:
        no_descanso_weekdays = [0]

    no_descanso_weekdays = [x for x in no_descanso_weekdays if 0 <= x <= 4]
    if not no_descanso_weekdays:
        no_descanso_weekdays = [0]

    # ✅ FILTRAR DÍAS VÁLIDOS
    dias_validos = [d for d in dias_descanso if d.weekday() not in no_descanso_weekdays]
    dias_validos = sorted(dias_validos)


    # ✅ VALIDACIÓN
    if len(dias_validos) < len(titulares_db):
        raise Exception("No hay suficientes días disponibles para descansos")

    # ✅ ROTACIÓN REAL (siempre cambia)
    offset = int(time.time()) % len(titulares_db)
    titulares_rotados = titulares_db[offset:] + titulares_db[:offset]

    # ✅ ASIGNAR DESCANSOS
    descansos_semana = {}

    for i, titular in enumerate(titulares_rotados):
        descansos_semana[titular[0]] = dias_validos[i]

    # 🔹 GENERAR SEMANA
    for i in range(7):
        dia = inicio + timedelta(days=i)
        descanso = None

        if dia.weekday() < 5:
            for pid, d_desc in descansos_semana.items():
                if d_desc == dia:
                    descanso = next(p for p in titulares_db if p[0] == pid)
                    break

        if descanso:
            cursor.execute(
                "INSERT INTO descansos (fecha, persona_id) VALUES (?, ?)",
                (dia, descanso[0])
            )

        # trabajadores activos
        trabajadores = [p for p in titulares_db if p != descanso]

        if descanso:
            trabajadores.append(backup_db)

            cursor.execute(
                "INSERT INTO reemplazos (fecha, reemplaza_a, persona_id) VALUES (?, ?, ?)",
                (dia, descanso[0], backup_db[0])
            )

        # asignar turnos
        ok = False
        for _ in range(200):
            temp = trabajadores[:]
            random.shuffle(temp)

            turno_A = temp[:2]
            turno_B = temp[2:]

            if valida_conflictos(turno_A, turno_B):
                ok = True
                break

        if not ok:
            turno_A = temp[:2]
            turno_B = temp[2:]

        for p in turno_A:
            cursor.execute(
                "INSERT INTO turnos (fecha, tipo, persona_id) VALUES (?, 'A', ?)",
                (dia, p[0])
            )

        for p in turno_B:
            cursor.execute(
                "INSERT INTO turnos (fecha, tipo, persona_id) VALUES (?, 'B', ?)",
                (dia, p[0])
            )

    db.commit()
    return {"mensaje": "✅ Turnos generados"}


@app.route("/agenda")
def agenda():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT t.fecha, t.tipo, p.nombre
        FROM turnos t
        JOIN personas p ON p.id = t.persona_id
        ORDER BY t.fecha
    """)
    turnos = cursor.fetchall()

    cursor.execute("""
        SELECT d.fecha, p.nombre
        FROM descansos d
        JOIN personas p ON p.id = d.persona_id
    """)
    descansos = cursor.fetchall()

    resultado = {}

    dias_semana = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }

    for f, tipo, nombre in turnos:
        if f not in resultado:
            dt = date.fromisoformat(str(f))
            resultado[f] = {
                "A": [],
                "B": [],
                "descanso": "",
                "diaSemana": dias_semana[dt.weekday()]
            }

        resultado[f][tipo].append(nombre)

    for f, nombre in descansos:
        if f in resultado:
            resultado[f]["descanso"] = nombre

    return jsonify(resultado)


if __name__ == "__main__":
    app.run(debug=True)