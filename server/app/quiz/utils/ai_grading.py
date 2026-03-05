import re

from rapidfuzz import fuzz


def fuzzy_similarity(a, b):

    """Returns a similarity score (0–100) using fuzzy matching."""

    return fuzz.token_set_ratio(str(a), str(b))


def normalize_answer(ans: str) -> str:

    """Cleans answer strings (removes option letters, prefixes, punctuation)."""

    ans = str(ans).strip()

    ans = re.sub(r"^[A-D]\)\s*", "", ans, flags=re.IGNORECASE)

    ans = re.sub(r"^correct answer[:\-]?\s*", "", ans, flags=re.IGNORECASE)

    return ans.strip()


def grade_with_ai(user_answers):

    result = []


    for answer in user_answers:

        question_type = answer.get("question_type", "").strip().lower()


        if question_type == "true-false":

            try:

                user_answer = int(answer.get("user_answer", -1))

                correct_answer = int(answer.get("correct_answer", -1))

            except ValueError:

                result.append({

                    "question": answer.get("question", ""),

                    "user_answer": answer.get("user_answer", ""),

                    "correct_answer": answer.get("correct_answer", ""),

                    "question_type": question_type,

                    "is_correct": False,

                    "result": "Invalid format"

                })

                continue


            is_correct = user_answer == correct_answer

            result.append({

                "question": answer.get("question", ""),

                "user_answer": user_answer,

                "correct_answer": correct_answer,

                "question_type": question_type,

                "is_correct": is_correct,

                "result": "Correct" if is_correct else "Incorrect"

            })

            continue

        user_answer = normalize_answer(answer.get("user_answer", ""))

        correct_answer = normalize_answer(answer.get("correct_answer", ""))


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


        elif question_type == "multichoice":

            is_correct = user_answer.lower() == correct_answer.lower()

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

