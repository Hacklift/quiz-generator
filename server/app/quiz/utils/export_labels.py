"""Offline export labels; quiz content itself is never retranslated on download."""
LABELS = {
    "en": {"title": "Quiz Download", "type": "Type", "description": "Description", "question": "Question", "questions": "Questions", "answer": "Answer", "explanation": "Explanation"},
    "es": {"title": "Descarga del cuestionario", "type": "Tipo", "description": "Descripción", "question": "Pregunta", "questions": "Preguntas", "answer": "Respuesta", "explanation": "Explicación"},
    "fr": {"title": "Téléchargement du questionnaire", "type": "Type", "description": "Description", "question": "Question", "questions": "Questions", "answer": "Réponse", "explanation": "Explication"},
}
TYPES = {
    "es": {"multichoice": "Opción múltiple", "true-false": "Verdadero o falso", "short-answer": "Respuesta corta", "open-ended": "Pregunta abierta"},
    "fr": {"multichoice": "Choix multiple", "true-false": "Vrai ou faux", "short-answer": "Réponse courte", "open-ended": "Question ouverte"},
}


def export_labels(payload):
    return LABELS.get(payload.get("content_locale"), LABELS["en"])


def export_type(payload):
    value = payload.get("quiz_type") or "quiz"
    return TYPES.get(payload.get("content_locale"), {}).get(value, value)
