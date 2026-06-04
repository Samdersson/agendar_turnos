from flask import Flask, jsonify, render_template, request
import os
import sqlite3
import random
from datetime import date, timedelta

app = Flask(__name__)



def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
    return sqlite3.connect(db_path)


# ✅ Página principal (abre index.html)
@app.route("/")
def index():
    return render_template("index.html")


# ✅ Generar turnos automáticamente
from flask import request


@app.route("/generar", methods=["POST", "GET"])
def generar():

    db = get_db()
    cursor = db.cursor()

    # Restricciones enviadas desde el front (pares que NO deben trabajar juntos)
    conflict_pairs = []
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        conflict_pairs = payload.get('conflictPairs', []) or []

    # Normalizar
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
    titulares = ["Mile", "Eli", "Juli", "May"]
    backup = ["Reemplazo"]

    # Regla de descansos:
    # - Cada titular tiene como máximo 1 descanso por semana.
    # - Descansos solo de lunes a viernes.
    # - Sábados y domingos: nadie descansa.

    descanso_usado = {}  # se completa después
    for p in titulares:
        cursor.execute("INSERT INTO personas (nombre, rol) VALUES (?, 'titular')", (p,))
    for p in backup:
        cursor.execute("INSERT INTO personas (nombre, rol) VALUES (?, 'backup')", (p,))


    db.commit()

    cursor.execute("SELECT id, nombre, rol FROM personas")
    personas = cursor.fetchall()

    titulares_db = [p for p in personas if p[2] == 'titular']
    backup_db = [p for p in personas if p[2] == 'backup'][0]

    descanso_usado = {p[0]: False for p in titulares_db}

    inicio = date.today()
    base = inicio.toordinal()

    def nombres_personas(personas_list):
        # personas_list: [(id,nombre,rol), ...]
        return [p[1] for p in personas_list]

    def valida_conflictos(turno_A, turno_B):
        # Restricción (modo B según confirmación):
        # No pueden trabajar juntos dentro del mismo turno,
        # o sea, no puede existir un par prohibido dentro de Turno A (entre sí)
        # ni dentro de Turno B (entre sí). 
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

    for i in range(7):
        dia = inicio + timedelta(days=i)

        descanso = None

        # 👉 descanso lunes a viernes (máx 1 por empleado en la semana)
        # Se rota usando el índice del día (i), así los descansos se reparten entre Lunes..Viernes.
        # Nota: si ya se usó el titular que toca, se toma el siguiente disponible.
        if dia.weekday() < 5:
            idx = (base + i) % len(titulares_db)
            candidato = titulares_db[idx]

            if descanso_usado.get(candidato[0], False):
                # buscar el siguiente titular disponible respetando la rotación
                for j in range(len(titulares_db)):
                    alt = titulares_db[(idx + j) % len(titulares_db)]
                    if not descanso_usado.get(alt[0], False):
                        candidato = alt
                        break

            descanso = candidato
            descanso_usado[descanso[0]] = True

            cursor.execute(
                "INSERT INTO descansos (fecha, persona_id) VALUES (?, ?)",
                (dia, descanso[0])
            )



        # 👉 trabajadores activos
        trabajadores = [p for p in titulares_db if p != descanso]

        # 👉 entra backup si alguien descansa
        if descanso:
            trabajadores.append(backup_db)

            cursor.execute(
                "INSERT INTO reemplazos (fecha, reemplaza_a, persona_id) VALUES (?, ?, ?)",
                (dia, descanso[0], backup_db[0])
            )

        # Asignar turnos evitando conflictos (reintentos con shuffle)
        ok = False
        for _ in range(200):
            
            trabajadores = trabajadores[:]
            random.shuffle(trabajadores)

            turno_A = trabajadores[:2]
            turno_B = trabajadores[2:]

            if valida_conflictos(turno_A, turno_B):
                ok = True
                break

        if not ok:
            # Si no se puede cumplir por restricciones extremas, igual asignamos la última mezcla
            turno_A = trabajadores[:2]
            turno_B = trabajadores[2:]

        # guardar turnos
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



# ✅ Obtener agenda
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

    # organizar datos
    for f, tipo, nombre in turnos:
        if f not in resultado:
            # f viene como string 'YYYY-MM-DD'
            dt = date.fromisoformat(str(f))
            resultado[f] = {"A": [], "B": [], "descanso": "", "diaSemana": dias_semana[dt.weekday()]}

        resultado[f][tipo].append(nombre)

    for f, nombre in descansos:
        if f in resultado:
            resultado[f]["descanso"] = nombre

    return jsonify(resultado)


# ✅ ejecutar app
if __name__ == "__main__":
    app.run(debug=True)