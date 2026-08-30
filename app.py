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
    titulares = ["Mile", "Dai", "Juli", "May",]
    backup = ["Ale"]

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


@app.route("/guardar_turnos", methods=["POST"])
def guardar_turnos():
    """Guarda los turnos de la tabla (posiblemente editados) en la base de datos."""
    db = get_db()
    cursor = db.cursor()

    payload = request.get_json(silent=True) or {}
    filas = payload.get('tabla', []) or []

    if not filas:
        return {"mensaje": "⚠️ No hay datos para guardar", "filas": 0}

    # Mapeo de nombre de día a weekday (0=Lunes ... 6=Domingo)
    dias_semana = {
        "Lunes": 0,
        "Martes": 1,
        "Miércoles": 2,
        "Jueves": 3,
        "Viernes": 4,
        "Sábado": 5,
        "Domingo": 6,
    }

    hoy = date.today()
    # Lunes de la semana actual
    lunes = hoy - timedelta(days=hoy.weekday())

    # Limpiar datos existentes de la semana actual
    cursor.execute("DELETE FROM turnos WHERE fecha >= ?", (lunes.isoformat(),))
    cursor.execute("DELETE FROM descansos WHERE fecha >= ?", (lunes.isoformat(),))
    cursor.execute("DELETE FROM reemplazos WHERE fecha >= ?", (lunes.isoformat(),))

    # Cargar personas existentes
    cursor.execute("SELECT id, nombre, rol FROM personas")
    personas = cursor.fetchall()
    persona_map = {p[1]: (p[0], p[2]) for p in personas}

    def get_persona_id(nombre):
        nombre = (nombre or '').strip()
        if not nombre:
            return None
        if nombre in persona_map:
            return persona_map[nombre][0]
        # Crear persona nueva si no existe
        cursor.execute("INSERT INTO personas (nombre, rol) VALUES (?, 'titular')", (nombre,))
        pid = cursor.lastrowid
        persona_map[nombre] = (pid, 'titular')
        return pid

    filas_guardadas = 0

    for fila in filas:
        dia_nombre = (fila.get('dia') or '').strip()
        turnoA = (fila.get('turnoA') or '').strip()
        turnoB = (fila.get('turnoB') or '').strip()
        descanso = (fila.get('descanso') or '').strip()

        if dia_nombre not in dias_semana:
            continue

        # Calcular la fecha real de este día (en la semana actual)
        weekday = dias_semana[dia_nombre]
        fecha_dia = lunes + timedelta(days=weekday)

        # Insertar turno A
        for nombre in [n.strip() for n in turnoA.split(',') if n.strip()]:
            pid = get_persona_id(nombre)
            if pid:
                cursor.execute(
                    "INSERT INTO turnos (fecha, tipo, persona_id) VALUES (?, 'A', ?)",
                    (fecha_dia.isoformat(), pid)
                )
                filas_guardadas += 1

        # Insertar turno B
        for nombre in [n.strip() for n in turnoB.split(',') if n.strip()]:
            pid = get_persona_id(nombre)
            if pid:
                cursor.execute(
                    "INSERT INTO turnos (fecha, tipo, persona_id) VALUES (?, 'B', ?)",
                    (fecha_dia.isoformat(), pid)
                )
                filas_guardadas += 1

        # Insertar descanso
        if descanso and descanso != '-':
            pid = get_persona_id(descanso)
            if pid:
                cursor.execute(
                    "INSERT INTO descansos (fecha, persona_id) VALUES (?, ?)",
                    (fecha_dia.isoformat(), pid)
                )

    db.commit()
    return {"mensaje": "✅ Turnos guardados en la base de datos", "filas": filas_guardadas}


if __name__ == "__main__":
    app.run(debug=True)
