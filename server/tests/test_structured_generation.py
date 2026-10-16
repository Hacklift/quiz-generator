import pytest

from server.app.quiz.utils.structured_generation import parse_generated_quiz


def test_true_false_uses_locale_labels_but_boolean_correctness():
    result = parse_generated_quiz(
        '{"content_locale":"fr","title":"Titre","description":"Explication",'
        '"questions":[{"question":"Q","explanation":"E",'
        '"options":null,"answer":null,"correct_boolean":false}]}',
        locale="fr",
        question_type="true-false",
        count=1,
    )
    assert result["questions"][0]["options"] == ["Vrai", "Faux"]
    assert result["questions"][0]["answer"] == "Faux"
    assert result["questions"][0]["correct_boolean"] is False


def test_generation_rejects_wrong_locale_and_missing_explanation():
    with pytest.raises(ValueError):
        parse_generated_quiz(
            '{"content_locale":"en","title":"Title","description":"D","questions":[]}',
            locale="es", question_type="multichoice", count=0,
        )

    with pytest.raises(ValueError):
        parse_generated_quiz(
            '{"content_locale":"es","title":"Título","description":"D",'
            '"questions":[{"question":"Q","explanation":"", "options":null,"answer":"A"}]}',
            locale="es", question_type="short-answer", count=1,
        )
