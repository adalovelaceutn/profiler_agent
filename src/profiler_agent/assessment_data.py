from __future__ import annotations

from profiler_agent.models import AssessmentDefinition


ASSESSMENTS: list[AssessmentDefinition] = [
    {
        "assessment_name": "Lovelace Everyday Life Profiling",
        "model": "Kolb Cycle",
        "scenarios": [
            {
                "id": 1,
                "dimension": "AE",
                "situation": "Te compras un electrodomestico complejo y nuevo que nunca usaste.",
                "options": [
                    {"text": "Lo enchufo y empiezo a tocar botones para ver que hace.", "score": 5},
                    {"text": "Busco en YouTube a alguien usandolo y luego pruebo una funcion.", "score": 3},
                    {"text": "No lo toco hasta haber leido las precauciones basicas.", "score": 1},
                ],
            },
            {
                "id": 2,
                "dimension": "RO",
                "situation": "Estas en una reunion social donde no conoces a casi nadie.",
                "options": [
                    {"text": "Me quedo un rato observando la dinamica del grupo antes de acercarme a hablar.", "score": 5},
                    {"text": "Escucho una conversacion y si me interesa, intervengo con una pregunta.", "score": 3},
                    {"text": "Entro directo saludando y me presento al primer grupo que veo.", "score": 1},
                ],
            },
            {
                "id": 3,
                "dimension": "AC",
                "situation": "Queres entender por que la economia del pais esta como esta.",
                "options": [
                    {"text": "Busco libros o articulos que expliquen las teorias y modelos economicos detras de la situacion.", "score": 5},
                    {"text": "Miro un resumen de noticias con las variables principales del mes.", "score": 3},
                    {"text": "Le pregunto a mis conocidos como les afecta el bolsillo en el dia a dia.", "score": 1},
                ],
            },
            {
                "id": 4,
                "dimension": "CE",
                "situation": "Tenes que elegir una pelicula para ver el fin de semana.",
                "options": [
                    {"text": "Elijo una que me genere una emocion fuerte o con la que me identifique personalmente.", "score": 5},
                    {"text": "Busco una que sea tendencia o que me hayan recomendado.", "score": 3},
                    {"text": "Prefiero un documental tecnico o una trama de logica muy compleja.", "score": 1},
                ],
            },
            {
                "id": 5,
                "dimension": "AE",
                "situation": "Estas cocinando una receta nueva y notas que la consistencia no es la correcta.",
                "options": [
                    {"text": "Empiezo a agregarle ingredientes a ojo para ver si se arregla en el momento.", "score": 5},
                    {"text": "Reviso la receta otra vez para ver si me salte un paso.", "score": 3},
                    {"text": "Tiro todo y empiezo de nuevo siguiendo las instrucciones con balanza.", "score": 1},
                ],
            },
            {
                "id": 6,
                "dimension": "RO",
                "situation": "Terminaste de jugar un partido (de futbol, padel, o un juego de mesa) y perdiste.",
                "options": [
                    {"text": "Me quedo pensando un buen rato en que jugadas falle y por que el otro gano.", "score": 5},
                    {"text": "Comento un par de errores con mis companeros y paso a otra cosa.", "score": 3},
                    {"text": "Me olvido del asunto apenas termina el juego.", "score": 1},
                ],
            },
            {
                "id": 7,
                "dimension": "AC",
                "situation": "Tenes que organizar tus vacaciones de verano.",
                "options": [
                    {"text": "Armo un cronograma detallado con mapas, distancias, presupuestos y opciones logicas.", "score": 5},
                    {"text": "Hago una lista de lugares que me gustaria visitar sin mucho orden.", "score": 3},
                    {"text": "Llego al lugar y decido que hacer cada manana segun como me despierte.", "score": 1},
                ],
            },
            {
                "id": 8,
                "dimension": "CE",
                "situation": "Para aprender a bailar un ritmo nuevo...",
                "options": [
                    {"text": "Necesito sentir la musica en el cuerpo y dejarme llevar por el movimiento.", "score": 5},
                    {"text": "Miro al profesor atentamente y trato de copiar sus pasos.", "score": 3},
                    {"text": "Estudio la estructura de los compases y cuento los pasos mentalmente (1, 2, 3...).", "score": 1},
                ],
            },
            {
                "id": 9,
                "dimension": "AE",
                "situation": "Hay un problema con el wifi en tu casa y no hay tecnicos disponibles.",
                "options": [
                    {"text": "Desconecto cables, reseteo el modem y pruebo combinaciones hasta que ande.", "score": 5},
                    {"text": "Busco el manual de usuario o un foro en internet con la solucion exacta.", "score": 3},
                    {"text": "Espero a que alguien que sepa mas que yo se encargue del tema.", "score": 1},
                ],
            },
            {
                "id": 10,
                "dimension": "RO",
                "situation": "Antes de dar tu opinion en una discusion importante...",
                "options": [
                    {"text": "Escucho todas las posturas y trato de entender el punto de vista de cada uno.", "score": 5},
                    {"text": "Pienso mi respuesta un segundo para no decir algo fuera de lugar.", "score": 3},
                    {"text": "Digo lo primero que siento, soy muy directo con mis ideas.", "score": 1},
                ],
            },
            {
                "id": 11,
                "dimension": "AC",
                "situation": "Te regalan un juego de estrategia de tablero muy complejo.",
                "options": [
                    {"text": "Disfruto planeando tacticas mentales y anticipando las jugadas de los demas.", "score": 5},
                    {"text": "Aprendo las reglas basicas y voy viendo que pasa durante la partida.", "score": 3},
                    {"text": "Prefiero los juegos de azar donde no haya que pensar tanto la estrategia.", "score": 1},
                ],
            },
            {
                "id": 12,
                "dimension": "CE",
                "situation": "Vas a un restaurante con un menu que tiene platos con nombres raros.",
                "options": [
                    {"text": "Me arriesgo a pedir algo desconocido confiando en mi instinto.", "score": 5},
                    {"text": "Pregunto al mozo que ingredientes tiene para darme una idea.", "score": 3},
                    {"text": "Pido lo mismo de siempre para no fallar.", "score": 1},
                ],
            },
        ],
    }
]
