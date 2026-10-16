from rapidfuzz import fuzz


def boolean_value(value):
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "vrai", "verdadero"}:
        return True
    if normalized in {"false", "0", "faux", "falso"}:
        return False
    return None


def fuzzy_similarity(a, b):

    return fuzz.token_set_ratio(str(a), str(b))


def grade_mock_answers(user_answers):

    result = []

    for answer in user_answers:

        question_type = answer.get("question_type", "").strip()

        user_answer = str(answer.get("user_answer", "")).strip()

        correct_answer = str(answer.get("correct_answer", "")).strip()


        if not correct_answer:

            continue


        if question_type == "open-ended":

            accuracy = fuzzy_similarity(user_answer, correct_answer)

            is_correct = accuracy >= 50

            result.append({

                "question": answer.get("question", ""),

                "user_answer": user_answer,

                "correct_answer": correct_answer,

                "question_type": question_type,

                "accuracy_percentage": accuracy,

                "is_correct": is_correct,

                "result": "Correct" if is_correct else "Incorrect"

            })


        elif question_type == "short-answer":

            accuracy = fuzzy_similarity(user_answer, correct_answer)

            is_correct = accuracy >= 80

            result.append({

                "question": answer.get("question", ""),

                "user_answer": user_answer,

                "correct_answer": correct_answer,

                "question_type": question_type,

                "accuracy_percentage": accuracy,

                "is_correct": is_correct,

                "result": "Correct" if is_correct else "Incorrect"

            })



        elif question_type in ["multichoice", "true-false"]:

            is_correct = (user_answer.lower() == correct_answer.lower())
            if question_type == "true-false":
                user_boolean = boolean_value(user_answer)
                correct_boolean = boolean_value(correct_answer)
                is_correct = user_boolean is not None and correct_boolean is not None and user_boolean == correct_boolean

            result.append({

                "question": answer.get("question", ""),

                "user_answer": user_answer,

                "correct_answer": correct_answer,

                "question_type": question_type,

                "is_correct": is_correct,

                "result": "Correct" if is_correct else "Incorrect"

            })

        else:

            result.append({

                "question": answer.get("question", ""),

                "user_answer": user_answer,

                "correct_answer": correct_answer,

                "question_type": question_type,

                "is_correct": False,

                "result": "Incorrect"

            })


    return result
