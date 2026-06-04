// Reglas de conflicto (pares que NO deben trabajar juntos).
// Se llenan desde el panel (front) o se puede dejar vacío para desactivar.

let conflictPairs = [];

function normalizeName(s) {
  return (s || '').trim();
}

function setConflictPairs(pairs) {
  // pairs: [{a:"Mile", b:"Eli"}, ...]
  conflictPairs = (pairs || [])
    .map(p => ({
      a: normalizeName(p.a),
      b: normalizeName(p.b)
    }))
    .filter(p => p.a && p.b && p.a !== p.b);
}

function isConflict(a, b) {
  a = normalizeName(a);
  b = normalizeName(b);
  if (!a || !b || a === b) return false;

  return conflictPairs.some(p =>
    (p.a === a && p.b === b) || (p.a === b && p.b === a)
  );
}

// Exponer global
window.ConflictRules = {
  setConflictPairs,
  isConflict,
  getConflictPairs: () => conflictPairs
};

