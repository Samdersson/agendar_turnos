// ✅ Manejo de restricciones desde el front
function agregarRestriccion() {
    const emp1 = document.getElementById('emp1').value;
    const emp2 = document.getElementById('emp2').value;

    if (emp1 === emp2) return;

    const pares = window.ConflictRules?.getConflictPairs?.() || [];

    // Evitar duplicados
    const existe = pares.some(p => (p.a === emp1 && p.b === emp2) || (p.a === emp2 && p.b === emp1));
    if (existe) return;

    window.ConflictRules.setConflictPairs([...pares, { a: emp1, b: emp2 }]);
    renderRestricciones();
}

function renderRestricciones() {
    const ul = document.getElementById('restriccionesList');
    if (!ul) return;
    const pares = window.ConflictRules?.getConflictPairs?.() || [];

    ul.innerHTML = '';
    pares.forEach(p => {
        const li = document.createElement('li');
        li.textContent = `${p.a} ↔ ${p.b}`;
        ul.appendChild(li);
    });
}

// ✅ Generar nueva semana (envía restricciones al backend)
function generar() {
    const pares = window.ConflictRules?.getConflictPairs?.() || [];

    fetch("/generar", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conflictPairs: pares })
    })
        .then(res => res.json())
        .then(data => {
            console.log(data);
            cargar();
        });
}


// ✅ Cargar datos en la tabla
function cargar() {

    fetch("/agenda")
    .then(res => res.json())
    .then(data => {

        const tabla = document.getElementById("tabla");
        tabla.innerHTML = "";

        const diasSemana = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];

        // Ordenar por día de la semana (Lunes -> Domingo)
        const ordenDia = {
            'Lunes': 0,
            'Martes': 1,
            'Miércoles': 2,
            'Jueves': 3,
            'Viernes': 4,
            'Sábado': 5,
            'Domingo': 6,
        };

        const dias = Object.keys(data);

        dias.sort((a, b) => {
            const da = data[a].diaSemana || '';
            const db = data[b].diaSemana || '';
            return (ordenDia[da] ?? 999) - (ordenDia[db] ?? 999);
        });

        dias.forEach(dia => {
            let info = data[dia];

            let fila = `
                <tr>
                    <td>${info.diaSemana || ''}</td>
                    <td>${info.A.join(", ")}</td>
                    <td>${info.B.join(", ")}</td>
                    <td>${info.descanso || "-"}</td>
                </tr>
            `;

            tabla.innerHTML += fila;
        });


    })
    .catch(error => {
        console.error("Error cargando agenda:", error);
    });
}

// ✅ Cargar automáticamente al abrir
window.onload = function() {
    cargar();
};