import sqlite3

conn = sqlite3.connect("turnos.db")
cursor = conn.cursor()

cursor.executescript("""

CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    rol TEXT
);

CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE,
    tipo TEXT,
    persona_id INTEGER
);

CREATE TABLE IF NOT EXISTS descansos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE,
    persona_id INTEGER
);

CREATE TABLE IF NOT EXISTS reemplazos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE,
    reemplaza_a INTEGER,
    persona_id INTEGER
);

""")

conn.commit()
conn.close()

print("✅ Base de datos lista")
