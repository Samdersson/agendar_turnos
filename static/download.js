// Descarga del turno en un archivo .txt

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (m) => ({
    '&': '&amp;',
    '<': '<',
    '>': '>',
    '"': '"',
    "'": '&#39;'
  }[m]));
}

function obtenerTextoTurno() {
  const nombreSemana = document.getElementById('nombreSemana')?.value || '';

  const filas = Array.from(document.querySelectorAll('#tabla tr'));
  const lineas = [];
  lineas.push(`Semana: ${nombreSemana || '(sin nombre)'}`);
  lineas.push('');
  lineas.push('Día | Turno A | Turno B | Descanso');
  lineas.push('------------------------------------------');

  filas.forEach(tr => {
    const tds = tr.querySelectorAll('td');
    if (!tds || tds.length < 4) return;
    const dia = tds[0].innerText.trim();
    const turnoA = tds[1].innerText.trim();
    const turnoB = tds[2].innerText.trim();
    const descanso = tds[3].innerText.trim();
    lineas.push(`${dia} | ${turnoA} | ${turnoB} | ${descanso}`);
  });

  return lineas.join('\n');
}

function descargarTurno() {
  const texto = obtenerTextoTurno();

  const nombreSemana = (document.getElementById('nombreSemana')?.value || 'turno')
    .trim()
    .replace(/[^a-z0-9\-\_ ]/gi, '')
    .replace(/\s+/g, '_')
    .slice(0, 40);

  const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `${nombreSemana}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}

