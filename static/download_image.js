// Descarga del turno como imagen JPG con estilo tipo “tabla”

function getTablaDatos() {
  const nombreSemana = document.getElementById('nombreSemana')?.value || '';
  const filas = Array.from(document.querySelectorAll('#tabla tr'));

  const datos = filas.map(tr => {
    const tds = tr.querySelectorAll('td');
    return {
      dia: (tds[0]?.innerText || '').trim(),
      turnoA: (tds[1]?.innerText || '').trim(),
      turnoB: (tds[2]?.innerText || '').trim(),
      descanso: (tds[3]?.innerText || '').trim(),
    };
  });

  return { nombreSemana, datos };
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight, maxLines = 3) {
  const words = String(text || '').split(/\s+/);
  let line = '';
  let lines = [];

  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (ctx.measureText(test).width <= maxWidth) {
      line = test;
    } else {
      if (line) lines.push(line);
      line = w;
    }
  }
  if (line) lines.push(line);

  // limitar a maxLines
  if (lines.length > maxLines) {
    lines = lines.slice(0, maxLines);
    // marcar con … en la última línea
    const last = lines[maxLines - 1];
    while (ctx.measureText(last + '…').width > maxWidth && last.length > 0) {
      lines[maxLines - 1] = last.slice(0, -1);
    }
    lines[maxLines - 1] = lines[maxLines - 1] + '…';
  }

  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], x, y + i * lineHeight);
  }
}

function descargarTurnoJPG() {
  const { nombreSemana, datos } = getTablaDatos();

  const nombreArchivo = (nombreSemana || 'turno')
    .trim()
    .replace(/[^a-z0-9\-\_ ]/gi, '')
    .replace(/\s+/g, '_')
    .slice(0, 40);

  // Tamaño de imagen
  const width = 1400;
  const paddingX = 70;
  const headerH = 80;
  const rowH = 98;
  const marginTop = 140;

  const height = marginTop + headerH + datos.length * rowH + 80;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Fondo
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  // Título
  ctx.fillStyle = '#111';
  ctx.font = 'bold 38px Arial';
  ctx.fillText(`Turnos Dulzura mía`, paddingX, 55);

  ctx.font = 'bold 28px Arial';
  ctx.fillStyle = '#0b5ed7';
  ctx.fillText(`Semana: ${nombreSemana || '(sin nombre)'}`, paddingX, 95);

  // Cols
  // Día | Turno A | Turno B | Descanso
  const colWidths = {
    dia: 190,
    A: 420,
    B: 420,
    descanso: width - (paddingX * 2 + 190 + 420 + 420),
  };
  const x0 = paddingX;
  const xDia = x0;
  const xA = xDia + colWidths.dia;
  const xB = xA + colWidths.A;
  const xDesc = xB + colWidths.B;

  const tableLeft = paddingX;
  const tableRight = width - paddingX;

  // Header bar
  ctx.fillStyle = '#343a40';
  ctx.fillRect(tableLeft, marginTop + 20, tableRight - tableLeft, headerH);

  // Header text
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 26px Arial';

  ctx.textBaseline = 'middle';
  const headerY = marginTop + 20 + headerH / 2;

  ctx.fillText('Día', xDia + 18, headerY);
  ctx.fillText('Turno A', xA + 18, headerY);
  ctx.fillText('Turno B', xB + 18, headerY);
  ctx.fillText('Descanso', xDesc + 18, headerY);

  ctx.textBaseline = 'alphabetic';

  // Borde general
  ctx.strokeStyle = '#d0d7de';
  ctx.lineWidth = 2;

  // Dibujar filas
  for (let i = 0; i < datos.length; i++) {
    const y = marginTop + 20 + headerH + i * rowH;

    // fondo alternado
    ctx.fillStyle = i % 2 === 0 ? '#f8f9fa' : '#ffffff';
    ctx.fillRect(tableLeft, y, tableRight - tableLeft, rowH);

    // líneas de borde
    ctx.strokeRect(tableLeft, y, tableRight - tableLeft, rowH);

    // vertical separators
    ctx.beginPath();
    ctx.moveTo(xA, y);
    ctx.lineTo(xA, y + rowH);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(xB, y);
    ctx.lineTo(xB, y + rowH);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(xDesc, y);
    ctx.lineTo(xDesc, y + rowH);
    ctx.stroke();

    // Texto
    ctx.fillStyle = '#111';
    ctx.font = 'bold 24px Arial';

    // Día
    ctx.fillText(datos[i].dia, xDia + 18, y + 34);

    // Turnos
    ctx.fillStyle = '#0b5ed7';
    ctx.font = 'bold 22px Arial';
    wrapText(ctx, datos[i].turnoA, xA + 18, y + 32, colWidths.A - 36, 28, 3);

    ctx.fillStyle = '#fd7e14';
    ctx.font = 'bold 22px Arial';
    wrapText(ctx, datos[i].turnoB, xB + 18, y + 32, colWidths.B - 36, 28, 3);

    ctx.fillStyle = '#6c757d';
    ctx.font = 'italic 22px Arial';
    wrapText(ctx, datos[i].descanso || '-', xDesc + 18, y + 32, colWidths.descanso - 36, 28, 3);
  }

  // Exportar
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${nombreArchivo}.jpg`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, 'image/jpeg', 0.92);
}

window.descargarTurnoJPG = descargarTurnoJPG;


