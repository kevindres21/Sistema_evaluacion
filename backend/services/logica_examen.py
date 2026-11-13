import random
from supabase_client import supabase

def generar_preguntas_aleatorias():
    """
    Lógica del DoD: Selecciona 10 preguntas al azar de cada componente (total 30)
    y las devuelve mezcladas, sin revelar cuál es la respuesta correcta.
    """
    # 1. Traer todas las preguntas
    resp_bd = supabase.table('preguntas').select(
        'id_pregunta, id_componente, enunciado, opciones_respuesta(id_opcion, texto_opcion)'
    ).execute()
    
    todas = resp_bd.data

    # 2. Filtrar por componentes (1: Estadística, 2: Cálculo, 3: Geometría)
    estadistica = [p for p in todas if p['id_componente'] == 1]
    calculo = [p for p in todas if p['id_componente'] == 2]
    geometria = [p for p in todas if p['id_componente'] == 3]

    # 3. Validación de seguridad
    if len(estadistica) < 10 or len(calculo) < 10 or len(geometria) < 10:
        raise ValueError("No hay suficientes preguntas en el banco de datos.")

    # 4. Seleccionar 10 al azar de cada uno
    seleccionadas = (
        random.sample(estadistica, 10) + 
        random.sample(calculo, 10) + 
        random.sample(geometria, 10)
    )
    
    # 5. Mezclar las 30 para que no salgan agrupadas
    random.shuffle(seleccionadas)
    
    return seleccionadas

def calcular_nota(respuestas_estudiante):
    """
    Recibe las respuestas del estudiante, consulta la BD para ver cuáles son correctas 
    y calcula la nota sobre 5.0.
    """
    correctas = 0
    total = len(respuestas_estudiante)

    for resp in respuestas_estudiante:
        # Consultar si la opción elegida es la correcta en la BD
        opcion = supabase.table('opciones_respuesta').select('es_correcta').eq('id_opcion', resp['id_opcion_seleccionada']).execute()
        
        es_correcta = opcion.data[0]['es_correcta'] if opcion.data else False
        
        if es_correcta:
            correctas += 1

    nota = (correctas / total) * 5.0 if total > 0 else 0
    return correctas, nota