import { useState, useEffect } from 'react';
import { api } from './api'; 
import './App.css';

function App() {
  const [idEstudiante, setIdEstudiante] = useState('');
  const [idIntento, setIdIntento] = useState(null);
  const [preguntas, setPreguntas] = useState([]);
  const [respuestas, setRespuestas] = useState({});
  const [resultado, setResultado] = useState(null);
  const [diagnostico, setDiagnostico] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const [tiempoRestante, setTiempoRestante] = useState(90 * 60);

  useEffect(() => {
    if (idIntento && !resultado) {
      const timer = setInterval(() => {
        setTiempoRestante((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            enviarExamen(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [idIntento, resultado]);

  const formatoTiempo = (segundos) => {
    const m = Math.floor(segundos / 60).toString().padStart(2, '0');
    const s = (segundos % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const iniciarExamen = async (e) => {
    e.preventDefault();
    setCargando(true);
    setError(null);
    try {
      const data = await api.iniciarExamen(idEstudiante);
      setIdIntento(data.id_intento);
      setPreguntas(data.preguntas);
      setTiempoRestante(90 * 60);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const seleccionarOpcion = (idPregunta, idOpcion) => {
    setRespuestas({ ...respuestas, [idPregunta]: idOpcion });
  };

  const enviarExamen = async (porTiempo = false) => {
    if (!porTiempo && !window.confirm("¿Estás seguro de enviar el examen? No podrás cambiar tus respuestas.")) return;
    
    setCargando(true);
    try {
      const respuestasFormateadas = Object.keys(respuestas).map(idPregunta => ({
        id_pregunta: parseInt(idPregunta),
        id_opcion_seleccionada: respuestas[idPregunta]
      }));

      const dataCalificar = await api.calificarExamen(idIntento, respuestasFormateadas);
      setResultado(dataCalificar);

      const dataDiag = await api.obtenerDiagnostico(idIntento);
      setDiagnostico(dataDiag.diagnostico);

    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  if (resultado && diagnostico) {
    return (
      <div className="container">
        <h1>Resultados del Examen</h1>
        {resultado.tiempo_agotado && <p style={{color: 'red', fontWeight: 'bold'}}>⏰ {resultado.mensaje}</p>}
        
        <div className="card-resultado">
          <h2>Nota: {resultado.calificacion} / 5.0</h2>
          <p>Respondiste correctamente {resultado.correctas} preguntas.</p>
        </div>

        <div className="card-diagnostico">
          <h3>Diagnóstico Pedagógico (Gemini AI):</h3>
          <p>{diagnostico}</p>
        </div>
      </div>
    );
  }

  if (!idIntento) {
    return (
      <div className="container inicio">
        <h1>Sistema de Evaluación</h1>
        <p>Ingresa tu ID de estudiante para comenzar.</p>
        {error && <p className="error">{error}</p>}
        <form onSubmit={iniciarExamen} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <input 
            type="number" 
            placeholder="ID de Estudiante" 
            value={idEstudiante}
            onChange={(e) => setIdEstudiante(e.target.value)}
            required
          />
          <button type="submit" disabled={cargando}>
            {cargando ? 'Cargando...' : 'Comenzar Examen'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header-examen">
        <h1>Examen en Curso</h1>
        <div className="reloj">
          ⏳ Tiempo restante: {formatoTiempo(tiempoRestante)}
        </div>
      </div>
      
      <p>Responde las siguientes {preguntas.length} preguntas. Puedes enviar el examen antes de tiempo si lo deseas.</p>
      {error && <p className="error">{error}</p>}

      {preguntas.map((p, index) => (
        <div key={p.id_pregunta} className="pregunta-card">
          <h3>{index + 1}. {p.enunciado}</h3>
          <div className="opciones">
            {p.opciones_respuesta.map((opcion) => (
              <label key={opcion.id_opcion}>
                <input 
                  type="radio" 
                  name={`pregunta_${p.id_pregunta}`} 
                  value={opcion.id_opcion}
                  onChange={() => seleccionarOpcion(p.id_pregunta, opcion.id_opcion)}
                />
                {opcion.texto_opcion}
              </label>
            ))}
          </div>
        </div>
      ))}

      <button 
        className="btn-enviar" 
        onClick={() => enviarExamen(false)} 
        disabled={cargando}
      >
        {cargando ? 'Calificando...' : 'Enviar Examen'}
      </button>
    </div>
  );
}

export default App;