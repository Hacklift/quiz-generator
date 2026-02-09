from server.app.db.seed_data.seed_all_categories import assign_question_types


def test_assign_question_types_fills_missing():
    questions = [
        {"question": "Q1", "question_type": ""},
        {"question": "Q2"},
        {"question": "Q3", "question_type": "short answer"},
    ]

    result = assign_question_types(questions)

    assert result[0]["question_type"] != ""
    assert result[1]["question_type"] != ""
    assert result[2]["question_type"] == "short answer"
