import string

mock_multiple_choice_questions = [
    {
        "question": "What is the capital of France?",
        "options": ["Paris", "London", "Berlin", "Rome"],
        "answer": "Paris",
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Earth", "Mars", "Jupiter", "Saturn"],
        "answer": "Mars",
    },
    {
        "question": "Who wrote 'Hamlet'?",
        "options": ["Shakespeare", "Hemingway", "Tolstoy", "Fitzgerald"],
        "answer": "Shakespeare",
    },
    {
        "question": "Which is the largest ocean on Earth?",
        "options": ["Atlantic Ocean", "Indian Ocean", "Arctic Ocean", "Pacific Ocean"],
        "answer": "Pacific Ocean",
    },
    {
        "question": "In what year did World War II end?",
        "options": ["1945", "1918", "1939", "1965"],
        "answer": "1945",
    },
    {
        "question": "Who painted the Mona Lisa?",
        "options": ["Van Gogh", "Leonardo da Vinci", "Picasso", "Michelangelo"],
        "answer": "Leonardo da Vinci",
    },
    {
        "question": "Which element has the chemical symbol 'O'?",
        "options": ["Oxygen", "Gold", "Silver", "Iron"],
        "answer": "Oxygen",
    },
    {
        "question": "What is the smallest prime number?",
        "options": ["0", "1", "2", "3"],
        "answer": "2",
    },
    {
        "question": "What is the square root of 64?",
        "options": ["6", "7", "8", "9"],
        "answer": "8",
    },
    {
        "question": "What is the currency of Japan?",
        "options": ["Yen", "Won", "Dollar", "Rupee"],
        "answer": "Yen",
    },
]


for q in mock_multiple_choice_questions:
    options = q["options"]
    answer = q["answer"]

    # Create prefixed options
    prefixed_options = [f"{letter}) {opt}" for letter, opt in zip(string.ascii_uppercase, options)]
    q["options"] = prefixed_options

    # Match the correct answer with the prefixed one
    for opt in prefixed_options:
        if opt.endswith(answer):
            q["answer"] = opt
            break

# === Optional: Print updated data ===
from pprint import pprint
pprint(mock_multiple_choice_questions)