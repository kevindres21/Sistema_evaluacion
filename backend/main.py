from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

from supabase_client import supabase
from services.logica_examen import generar_preguntas_aleatorias, calcular_nota

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
modelo_gemini = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(title="Sistema de Evaluación API")

# --- MODELOS DE DATOS ---
class LoginEstudianteRequest(BaseModel):
    documento: str
    password: str

class RespuestaEstudiante(BaseModel):
    id_pregunta: int
    id_opcion_seleccionada: int

class EnviarExamenRequest(BaseModel):
    id_intento: int
    respuestas: List[RespuestaEstudiante]

# --- RUTA 1: INICIAR EXAMEN (Con Login) ---
@app.post("/api/examen/iniciar")
def iniciar_examen(request: LoginEstudianteRequest):
    try:
        # 1. Buscar al estudiante por documento y contraseña
        estudiante = supabase.table('estudiantes').select('*').eq('documento_identidad', request.documento).eq('password_hash', request.password).execute()
        
        if not estudiante.data:
            raise HTTPException(status_code=401, detail="Documento o contraseña incorrectos.")

        estudiante_id = estudiante.data[0]['id_estudiante']
        nombre_estudiante = estudiante.data[0]['nombres']

        # 2. Crear el registro en intentos_examen usando el ID real
        intento = supabase.table('intentos_examen').insert({
            "id_estudiante": estudiante_id,
            "estado": "En progreso"
        }).execute()
        
        id_intento = intento.data[0]['id_intento']

        # 3. Generar las 30 preguntas
        preguntas_examen = generar_preguntas_aleatorias()

        # 4. Guardar el detalle en la base de datos
        detalles = [{"id_intento": id_intento, "id_pregunta": p['id_pregunta']} for p in preguntas_examen]
        supabase.table('detalle_intento').insert(detalles).execute()

        return {
            "id_intento": id_intento, 
            "preguntas": preguntas_examen,
            "nombre": nombre_estudiante
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- RUTA 2: CALIFICAR EXAMEN (Con validación de tiempo) ---
@app.post("/api/examen/calificar")
def calificar_examen(request: EnviarExamenRequest):
    try:
        # 1. Buscar el intento
        intento_db = supabase.table('intentos_examen').select('*').eq('id_intento', request.id_intento).execute()
        if not intento_db.data:
            raise HTTPException(status_code=404, detail="Intento no encontrado")
        
        intento = intento_db.data[0]

        if intento['estado'] == 'Finalizado':
            raise HTTPException(status_code=400, detail="Este examen ya fue enviado y calificado.")

        # 2. Validar el tiempo (90 minutos = 1 hora y media)
        fecha_inicio_str = intento['fecha_inicio']
        fecha_inicio = datetime.fromisoformat(fecha_inicio_str.replace("Z", "+00:00"))
        ahora = datetime.now(timezone.utc)
        tiempo_transcurrido = ahora - fecha_inicio
        limite_tiempo = timedelta(minutes=90)

        tiempo_agotado = False
        if tiempo_transcurrido > limite_tiempo:
            tiempo_agotado = True

        # 3. Calcular la nota
        respuestas_dict = [r.dict() for r in request.respuestas]
        correctas, nota = calcular_nota(respuestas_dict)

        # 4. Actualizar el detalle de las preguntas respondidas
        for resp in request.respuestas:
            opcion = supabase.table('opciones_respuesta').select('es_correcta').eq('id_opcion', resp.id_opcion_seleccionada).execute()
            es_correcta = opcion.data[0]['es_correcta'] if opcion.data else False
            
            supabase.table('detalle_intento').update({
                "id_opcion_seleccionada": resp.id_opcion_seleccionada,
                "es_correcta": es_correcta
            }).eq('id_intento', request.id_intento).eq('id_pregunta', resp.id_pregunta).execute()

        # 5. Finalizar el intento
        supabase.table('intentos_examen').update({
            "calificacion": nota,
            "estado": "Finalizado",
            "fecha_fin": ahora.isoformat()
        }).eq('id_intento', request.id_intento).execute()

        mensaje = "Examen calificado exitosamente."
        if tiempo_agotado:
            mensaje = "El tiempo de 1 hora y 30 minutos ha finalizado. El examen se cerró y calificó automáticamente."

        return {
            "id_intento": request.id_intento, 
            "correctas": correctas, 
            "total": len(request.respuestas),
            "calificacion": round(nota, 2),
            "tiempo_agotado": tiempo_agotado,
            "mensaje": mensaje
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- RUTA 3: GENERAR DIAGNÓSTICO CON IA ---
@app.post("/api/examen/diagnostico/{id_intento}")
def generar_diagnostico(id_intento: int):
    try:
        intento = supabase.table('intentos_examen').select('calificacion').eq('id_intento', id_intento).execute()
        if not intento.data:
            raise HTTPException(status_code=404, detail="Intento no encontrado")
        
        nota = intento.data[0]['calificacion']

        prompt = f"Actúa como un tutor pedagógico. Un estudiante obtuvo {nota}/5.0 en un examen de Matemáticas (Estadística, Cálculo y Geometría). Genera un diagnóstico breve (máximo 3 párrafos) indicando qué áreas debe reforzar y dale 2 consejos prácticos de estudio."

        respuesta_ia = modelo_gemini.generate_content(prompt)
        texto_diagnostico = respuesta_ia.text

        supabase.table('diagnosticos_ia').insert({
            "id_intento": id_intento,
            "prompt_enviado": prompt,
            "respuesta_ia": texto_diagnostico
        }).execute()

        return {"id_intento": id_intento, "diagnostico": texto_diagnostico}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))