from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import google.generativeai as genai
from dotenv import load_dotenv

from supabase_client import supabase
# Importamos nuestra lógica separada
from services.logica_examen import generar_preguntas_aleatorias, calcular_nota

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
modelo_gemini = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(title="Sistema de Evaluación API")

# --- MODELOS DE DATOS ---
class IniciarExamenRequest(BaseModel):
    id_estudiante: int

class RespuestaEstudiante(BaseModel):
    id_pregunta: int
    id_opcion_seleccionada: int

class EnviarExamenRequest(BaseModel):
    id_intento: int
    respuestas: List[RespuestaEstudiante]

# --- RUTA 1: INICIAR EXAMEN ---
@app.post("/api/examen/iniciar")
def iniciar_examen(request: IniciarExamenRequest):
    try:
        # 1. Crear el registro en intentos_examen
        intento = supabase.table('intentos_examen').insert({
            "id_estudiante": request.id_estudiante,
            "estado": "En progreso"
        }).execute()
        
        id_intento = intento.data[0]['id_intento']

        # 2. Usar la lógica importada para sacar las 30 preguntas
        preguntas_examen = generar_preguntas_aleatorias()

        # 3. Guardar el detalle en la base de datos
        detalles = [{"id_intento": id_intento, "id_pregunta": p['id_pregunta']} for p in preguntas_examen]
        supabase.table('detalle_intento').insert(detalles).execute()

        return {"id_intento": id_intento, "preguntas": preguntas_examen}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- RUTA 2: CALIFICAR EXAMEN ---
@app.post("/api/examen/calificar")
def calificar_examen(request: EnviarExamenRequest):
    try:
        # Convertimos los objetos Pydantic a diccionarios para nuestra función
        respuestas_dict = [r.dict() for r in request.respuestas]
        
        # Usar la lógica importada para calcular la nota
        correctas, nota = calcular_nota(respuestas_dict)

        # Actualizar el detalle_intento fila por fila (para saber qué respondió)
        for resp in request.respuestas:
            opcion = supabase.table('opciones_respuesta').select('es_correcta').eq('id_opcion', resp.id_opcion_seleccionada).execute()
            es_correcta = opcion.data[0]['es_correcta'] if opcion.data else False
            
            supabase.table('detalle_intento').update({
                "id_opcion_seleccionada": resp.id_opcion_seleccionada,
                "es_correcta": es_correcta
            }).eq('id_intento', request.id_intento).eq('id_pregunta', resp.id_pregunta).execute()

        # Actualizar intento
        supabase.table('intentos_examen').update({
            "calificacion": nota,
            "estado": "Finalizado"
        }).eq('id_intento', request.id_intento).execute()

        return {"id_intento": request.id_intento, "correctas": correctas, "calificacion": round(nota, 2)}

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

        prompt = f"Actúa como un tutor pedagógico. Un estudiante obtuvo {nota}/5.0 en un examen de Matemáticas. Genera un diagnóstico breve (3 párrafos) y dale 2 consejos de estudio."

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