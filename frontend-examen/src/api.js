const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

export const api = {
  iniciarExamen: async (documento, password) => {
    const res = await fetch(`${BACKEND_URL}/api/examen/iniciar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documento: documento, password: password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al iniciar sesión. Verifica tus credenciales.');
    return data;
  },

  calificarExamen: async (idIntento, respuestas) => {
    const res = await fetch(`${BACKEND_URL}/api/examen/calificar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_intento: idIntento, respuestas })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al calificar");
    return data;
  },

  obtenerDiagnostico: async (idIntento) => {
    const res = await fetch(`${BACKEND_URL}/api/examen/diagnostico/${idIntento}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Error al generar el diagnóstico.');
    return await res.json();
  }
};