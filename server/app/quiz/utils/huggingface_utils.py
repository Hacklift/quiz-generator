import os
import re
from typing import Any, Dict, List, Union, Optional
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()
client = InferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))


# ====== PARSING FUNCTIONS ======

def parse_multichoice(response: str) -> List[Dict[str, Any]]:
    question_blocks = re.findall(
        r"\*\*\d+\. (.*?)\*\*\s+(.*?)\n\n\*\*Answer:\*\* ([A-D])",
        response,
        re.DOTALL
    )

    questions = []
    for question_text, options_block, correct_letter in question_blocks:
        options = re.findall(r"([A-D]\)) (.*?)\s{2,}", options_block + "  ", re.DOTALL)
        if not options:
            options = re.findall(r"([A-D]\)) (.*?)\n", options_block)

        formatted_options = [f"{opt[0]} {opt[1].strip()}" for opt in options]

        # Convert "A"/"B"/"C"/"D" into full text option
        idx = ord(correct_letter.strip().upper()) - ord("A")
        correct_answer = formatted_options[idx] if 0 <= idx < len(formatted_options) else correct_letter

        questions.append({
            "question": question_text.strip(),
            "options": formatted_options,
            "answer": correct_answer,
            "question_type": "multichoice"
        })
    return questions


def parse_true_false(response: str) -> List[Dict[str, Any]]:
    """Parse true/false questions from model response."""
    question_blocks = re.findall(
        r"\*\*\d+\. (.*?)\*\*\n\n\*\*Answer:\*\* (True|False)",
        response,
        re.DOTALL | re.IGNORECASE
    )

    return [
        {
            "question": q.strip(),
            "options": ["True", "False"],
            "answer": ans.strip().capitalize(),
            "question_type": "true-false"
        }
        for q, ans in question_blocks
    ]


def parse_open_ended(response: str) -> List[Dict[str, Any]]:
    """Parse open-ended questions (longer answers)."""
    question_blocks = re.findall(
        r"\*\*\d+\. (.*?)\*\*\n\n\*\*Answer:\*\* (.+)",
        response,
        re.DOTALL
    )
    return [
        {
            "question": q.strip(),
            "answer": ans.strip(),
            "question_type": "open-ended"
        }
        for q, ans in question_blocks
    ]


def parse_short_answer(response: str) -> List[Dict[str, Any]]:
    """Parse short-answer questions (1–3 words)."""
    return [
        {**item, "question_type": "short-answer"}
        for item in parse_open_ended(response)
    ]

# ====== PROMPT BUILDER ======

def build_prompt(profession: str, question_type: str, difficulty_level: str, num_questions: int, audience_type: str, custom_instruction: Optional[str]) -> str:
    type_formats = {
        "multichoice": """
Each question should be clearly numbered and provide options A–D, with the correct answer stated after each question.
Format:
**1. Question here**
A) Option A  
B) Option B  
C) Option C  
D) Option D  

**Answer:** A
""",
        "true-false": """
Each question should be clearly numbered, followed by the correct answer ("True" or "False").
Format:
**1. Question here**

**Answer:** True
""",
        "open-ended": """
Each question should be clearly numbered, followed by the correct answer in a few words or one sentence.
Format:
**1. Question here**

**Answer:** Correct answer here
""",
        "short-answer": """
Each question should be clearly numbered, followed by the correct answer in 1–3 words.
Format:
**1. Question here**

**Answer:** Correct answer here
"""
    }

    custom_part = f"\nAdditional instructions: {custom_instruction}" if custom_instruction else ""
    return f"""
Generate a {difficulty_level} difficulty {question_type} quiz with {num_questions} questions on {profession}.
The quiz is intended for {audience_type} learners.
{type_formats.get(question_type, type_formats['multichoice'])}
{custom_part}
"""


# ====== MAIN FUNCTION ======

def generate_quiz_with_huggingface(payload: Dict[str, Any]) -> Dict[str, Any]:
    profession = payload.get("profession", "General Knowledge")
    question_type = payload.get("question_type", "multichoice").lower()
    difficulty_level = payload.get("difficulty_level", "medium")
    num_questions = int(payload.get("num_questions", 5))
    audience_type = payload.get("audience_type", "general")
    custom_instruction = payload.get("custom_instruction")

    prompt = build_prompt(
        profession, question_type, difficulty_level, num_questions, audience_type, custom_instruction
    )

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3-0324",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.7
    )

    response_text = response.choices[0].message.content

    # Select parser based on question type
    if question_type == "multichoice":
        questions = parse_multichoice(response_text)
    elif question_type == "true-false":
        questions = parse_true_false(response_text)
    elif question_type == "open-ended":
        questions = parse_open_ended(response_text)
    elif question_type == "short-answer":
        questions = parse_short_answer(response_text)
    else:
        return {"error": f"Unsupported question type: {question_type}", "raw": response_text}

    return {
        "message": "Quiz generated successfully",
        "profession": profession,
        "num_questions": num_questions,
        "question_type": question_type,
        "difficulty_level": difficulty_level,
        "audience_type": audience_type,
        "custom_instruction": custom_instruction,
        "questions": questions
    }
