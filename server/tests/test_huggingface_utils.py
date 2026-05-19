from server.app.quiz.utils.huggingface_utils import parse_multichoice


def test_parse_multichoice_preserves_wrapped_option_lines():
    response = """
**1. Which statement best describes the design goal?**
A) The option begins here and continues
onto a second line for extra detail
B) Short option
C) Another short option
D) Final option

**Answer:** A
"""

    questions = parse_multichoice(response)

    assert len(questions) == 1
    assert questions[0]["options"][0] == (
        "A) The option begins here and continues onto a second line for extra detail"
    )
    assert questions[0]["answer"] == (
        "A) The option begins here and continues onto a second line for extra detail"
    )
