"""Bundled general-knowledge samples; never generated from user material."""
from random import sample, shuffle

from fastapi import HTTPException

from server.app.quiz.utils.structured_generation import QUESTION_TYPES, normalize_questions

SAMPLE_LIMIT = 10
SAMPLE_LOCALES = {"en", "es", "fr"}

# question, correct answer, distractors, explanation, true/false statement, truth
FACTS = {
    "en": [
        ("How many sides does a triangle have?", "Three", ["Two", "Four", "Five"], "A triangle is a polygon with three sides.", "A triangle has four sides.", False),
        ("Which planet do humans live on?", "Earth", ["Mars", "Venus", "Jupiter"], "Earth is the planet where humans live.", "Humans live on Earth.", True),
        ("How many minutes are in an hour?", "60", ["30", "90", "100"], "One hour contains 60 minutes.", "An hour contains 100 minutes.", False),
        ("Which part of a plant usually absorbs water from soil?", "Roots", ["Flowers", "Fruit", "Seeds"], "Roots absorb water from the soil.", "Roots absorb water from soil.", True),
        ("What is seven multiplied by eight?", "56", ["48", "54", "64"], "Seven groups of eight make 56.", "Seven multiplied by eight equals 54.", False),
        ("What is the opposite of north?", "South", ["East", "West", "Northeast"], "North and south are opposite compass directions.", "South is opposite north.", True),
        ("What is frozen water called?", "Ice", ["Steam", "Sand", "Salt"], "Ice is water in its solid state.", "Frozen water is called steam.", False),
        ("How many days are in a week?", "Seven", ["Five", "Six", "Eight"], "A week contains seven days.", "A week has seven days.", True),
        ("Which instrument measures temperature?", "Thermometer", ["Ruler", "Clock", "Compass"], "A thermometer measures temperature.", "A ruler measures temperature.", False),
        ("How many sides does a square have?", "Four", ["Three", "Five", "Six"], "A square has four equal sides.", "A square has four sides.", True),
    ],
    "es": [
        ("¿Cuántos lados tiene un triángulo?", "Tres", ["Dos", "Cuatro", "Cinco"], "Un triángulo es un polígono de tres lados.", "Un triángulo tiene cuatro lados.", False),
        ("¿En qué planeta viven los seres humanos?", "La Tierra", ["Marte", "Venus", "Júpiter"], "La Tierra es el planeta donde viven los seres humanos.", "Los seres humanos viven en la Tierra.", True),
        ("¿Cuántos minutos tiene una hora?", "60", ["30", "90", "100"], "Una hora tiene 60 minutos.", "Una hora tiene 100 minutos.", False),
        ("¿Qué parte de una planta suele absorber agua del suelo?", "Las raíces", ["Las flores", "Los frutos", "Las semillas"], "Las raíces absorben agua del suelo.", "Las raíces absorben agua del suelo.", True),
        ("¿Cuánto es siete por ocho?", "56", ["48", "54", "64"], "Siete grupos de ocho suman 56.", "Siete por ocho es igual a 54.", False),
        ("¿Cuál es la dirección opuesta al norte?", "Sur", ["Este", "Oeste", "Noreste"], "El norte y el sur son direcciones opuestas de la brújula.", "El sur es la dirección opuesta al norte.", True),
        ("¿Cómo se llama el agua congelada?", "Hielo", ["Vapor", "Arena", "Sal"], "El hielo es agua en estado sólido.", "El agua congelada se llama vapor.", False),
        ("¿Cuántos días tiene una semana?", "Siete", ["Cinco", "Seis", "Ocho"], "Una semana tiene siete días.", "Una semana tiene siete días.", True),
        ("¿Qué instrumento mide la temperatura?", "Termómetro", ["Regla", "Reloj", "Brújula"], "Un termómetro mide la temperatura.", "Una regla mide la temperatura.", False),
        ("¿Cuántos lados tiene un cuadrado?", "Cuatro", ["Tres", "Cinco", "Seis"], "Un cuadrado tiene cuatro lados iguales.", "Un cuadrado tiene cuatro lados.", True),
    ],
    "fr": [
        ("Combien de côtés possède un triangle ?", "Trois", ["Deux", "Quatre", "Cinq"], "Un triangle est un polygone à trois côtés.", "Un triangle possède quatre côtés.", False),
        ("Sur quelle planète vivent les humains ?", "La Terre", ["Mars", "Vénus", "Jupiter"], "La Terre est la planète où vivent les humains.", "Les humains vivent sur la Terre.", True),
        ("Combien de minutes y a-t-il dans une heure ?", "60", ["30", "90", "100"], "Une heure contient 60 minutes.", "Une heure contient 100 minutes.", False),
        ("Quelle partie d'une plante absorbe généralement l'eau du sol ?", "Les racines", ["Les fleurs", "Les fruits", "Les graines"], "Les racines absorbent l'eau du sol.", "Les racines absorbent l'eau du sol.", True),
        ("Combien font sept fois huit ?", "56", ["48", "54", "64"], "Sept groupes de huit font 56.", "Sept fois huit font 54.", False),
        ("Quelle direction est opposée au nord ?", "Le sud", ["L'est", "L'ouest", "Le nord-est"], "Le nord et le sud sont des directions opposées sur une boussole.", "Le sud est opposé au nord.", True),
        ("Comment appelle-t-on l'eau gelée ?", "La glace", ["La vapeur", "Le sable", "Le sel"], "La glace est de l'eau à l'état solide.", "L'eau gelée s'appelle la vapeur.", False),
        ("Combien de jours y a-t-il dans une semaine ?", "Sept", ["Cinq", "Six", "Huit"], "Une semaine compte sept jours.", "Une semaine compte sept jours.", True),
        ("Quel instrument mesure la température ?", "Un thermomètre", ["Une règle", "Une horloge", "Une boussole"], "Un thermomètre mesure la température.", "Une règle mesure la température.", False),
        ("Combien de côtés possède un carré ?", "Quatre", ["Trois", "Cinq", "Six"], "Un carré possède quatre côtés égaux.", "Un carré possède quatre côtés.", True),
    ],
}
COPY = {
    "en": ("Sample quiz: general knowledge", "Saved sample questions. Not AI-generated or tailored to your topic, difficulty, or document."),
    "es": ("Cuestionario de ejemplo: cultura general", "Preguntas de ejemplo guardadas. No generadas por IA ni adaptadas a tu tema, nivel de dificultad o documento."),
    "fr": ("Quiz d'exemple : culture générale", "Questions d'exemple enregistrées. Elles ne sont pas générées par l'IA ni adaptées à votre sujet, niveau de difficulté ou document."),
}


def get_sample_quiz(locale: str, question_type: str, count: int) -> dict:
    if question_type not in QUESTION_TYPES:
        raise HTTPException(422, "Unsupported question type")
    if locale not in SAMPLE_LOCALES or not 1 <= count <= SAMPLE_LIMIT:
        raise HTTPException(503, "AI is unavailable. Saved samples support English, Spanish and French, with 1–10 questions. Retry or change your selection.")
    questions = []
    for question, answer, distractors, explanation, statement, truth in sample(FACTS[locale], count):
        item = {"question": question, "answer": answer, "explanation": explanation}
        if question_type == "multichoice":
            options = [answer, *distractors]
            shuffle(options)
            item.update(options=options, correct_option_index=options.index(answer))
        elif question_type == "true-false":
            item.update(question=statement, correct_boolean=truth)
        questions.append(item)
    return {
        "title": COPY[locale][0], "description": COPY[locale][1],
        "content_locale": locale, "source": "mock",
        "questions": normalize_questions({"questions": questions}, locale=locale, question_type=question_type, count=count),
    }
