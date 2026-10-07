import os

from pathlib import Path

import re

import asyncio

import functools

from typing import Any, Dict, List, Optional

from huggingface_hub import InferenceClient

from dotenv import load_dotenv

from server.app.quiz.repositories.token_repository import get_user_token


env_path = Path(__file__).resolve().parents[3] / ".env"

load_dotenv(dotenv_path=env_path)


load_dotenv()

HF_FALLBACK_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")


AI_CHATTER_PATTERN = re.compile(
    r"(?i)\s*-{2,}\s*(?:let me know|tell me|feel free|hope this helps|would you like|do you want)[^\n]*"
)
ANSWER_TRAILER_PATTERN = re.compile(r"(?is)\s*\bAnswer\s*:\s*.*$")
SEPARATOR_PATTERN = re.compile(r"\s*-{2,}\s*")


def sanitize_generated_text(value: Any, *, strip_answer_trailer: bool = False) -> str:
    """Remove assistant chatter and formatting artifacts before persisting quiz data."""

    if value is None:
        return ""

    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"```(?:\w+)?", "", text)
    text = text.replace("```", "")
    text = AI_CHATTER_PATTERN.sub("", text)
    if strip_answer_trailer:
        text = ANSWER_TRAILER_PATTERN.sub("", text)
    text = SEPARATOR_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -*\n\t")


def split_question_blocks(response: str) -> list[str]:
    cleaned = str(response or "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"```(?:\w+)?", "", cleaned)
    cleaned = cleaned.replace("```", "")
    cleaned = AI_CHATTER_PATTERN.sub("", cleaned)
    matches = list(
        re.finditer(
            r"(?ms)(?:^|\n)\s*(?:\*\*)?\d+\.\s+.*?(?=(?:\n\s*(?:\*\*)?\d+\.\s+)|\Z)",
            cleaned,
        )
    )
    return [match.group(0).strip() for match in matches]


def parse_answer_letter(answer_text: str) -> str:
    match = re.search(r"\b([A-D])\b", answer_text, re.IGNORECASE)
    return match.group(1).upper() if match else sanitize_generated_text(answer_text)


def parse_answer_value(answer_text: str) -> str:
    answer = sanitize_generated_text(answer_text)
    answer = re.sub(r"^[A-D]\)\s*", "", answer, flags=re.IGNORECASE)
    return answer



def parse_multichoice(response: str) -> List[Dict[str, Any]]:
    """Parse multiple-choice questions with A-D options, including wrapped option lines."""

    answer_pattern = re.compile(r"(?:\*\*)?\s*Answer\s*:\s*(?:\*\*)?\s*(.+)$", re.IGNORECASE)
    option_pattern = re.compile(r"^([A-D])\)\s*(.*)$", re.IGNORECASE)

    questions = []

    for block in split_question_blocks(response):
        answer_match = answer_pattern.search(block)
        if not answer_match:
            continue

        answer_text = answer_match.group(1)
        before_answer = block[: answer_match.start()].strip()
        lines = [line.strip() for line in before_answer.splitlines() if line.strip()]
        if not lines:
            continue

        question_line = lines[0]
        question_text = re.sub(r"^(?:\*\*)?\d+\.\s*", "", question_line).strip()
        question_text = sanitize_generated_text(question_text, strip_answer_trailer=True)

        parsed_options: list[tuple[str, str]] = []
        current_letter = None
        current_text_parts: list[str] = []

        for raw_line in lines[1:]:
            line = raw_line.strip()
            if not line:
                continue

            option_match = option_pattern.match(line)
            if option_match:
                if current_letter and current_text_parts:
                    option_text = sanitize_generated_text(
                        " ".join(current_text_parts),
                        strip_answer_trailer=True,
                    )
                    if option_text:
                        parsed_options.append((current_letter, option_text))
                current_letter = option_match.group(1).upper()
                current_text_parts = [option_match.group(2).strip()]
            elif current_letter:
                current_text_parts.append(line)

        if current_letter and current_text_parts:
            option_text = sanitize_generated_text(
                " ".join(current_text_parts),
                strip_answer_trailer=True,
            )
            if option_text:
                parsed_options.append((current_letter, option_text))

        formatted_options = [f"{letter}) {text}" for letter, text in parsed_options if text]
        correct_letter = parse_answer_letter(answer_text)
        idx = ord(correct_letter) - ord("A") if len(correct_letter) == 1 else -1
        correct_answer = formatted_options[idx] if 0 <= idx < len(formatted_options) else parse_answer_value(answer_text)

        if question_text and len(formatted_options) == 4 and correct_answer:
            questions.append(
                {
                    "question": question_text,
                    "options": formatted_options,
                    "answer": correct_answer,
                    "question_type": "multichoice",
                }
            )

    return questions



def parse_true_false(response: str) -> List[Dict[str, Any]]:

    """Parse true/false questions."""

    question_blocks = []
    for block in split_question_blocks(response):
        answer_match = re.search(
            r"(?:\*\*)?\s*Answer\s*:\s*(?:\*\*)?\s*(True|False)\b",
            block,
            re.IGNORECASE,
        )
        if not answer_match:
            continue
        question_text = block[: answer_match.start()]
        question_text = re.sub(r"^(?:\*\*)?\d+\.\s*", "", question_text).strip()
        question_text = sanitize_generated_text(question_text, strip_answer_trailer=True)
        question_blocks.append((question_text, answer_match.group(1)))

    return [

        {

            "question": q,

            "options": ["True", "False"],

            "answer": ans.strip().capitalize(),

            "question_type": "true-false"

        }

        for q, ans in question_blocks

    ]



def parse_open_ended(response: str) -> List[Dict[str, Any]]:

    """Parse open-ended questions requiring longer answers."""

    question_blocks = []
    for block in split_question_blocks(response):
        answer_match = re.search(
            r"(?:\*\*)?\s*Answer\s*:\s*(?:\*\*)?\s*(.+)$",
            block,
            re.IGNORECASE | re.DOTALL,
        )
        if not answer_match:
            continue
        question_text = block[: answer_match.start()]
        question_text = re.sub(r"^(?:\*\*)?\d+\.\s*", "", question_text).strip()
        question_text = sanitize_generated_text(question_text, strip_answer_trailer=True)
        answer_text = sanitize_generated_text(answer_match.group(1))
        question_blocks.append((question_text, answer_text))

    return [

        {

            "question": q,

            "answer": ans,

            "question_type": "open-ended"

        }

        for q, ans in question_blocks

    ]



def parse_short_answer(response: str) -> List[Dict[str, Any]]:

    """Parse short-answer questions requiring 1–3 words."""

    return [

        {**item, "question_type": "short-answer"}

        for item in parse_open_ended(response)

    ]


def parse_matching(response: str) -> List[Dict[str, Any]]:
    """Parse matching blocks whose answer lists ``left -> right`` pairs."""
    questions = []
    answer_pattern = re.compile(r"(?:\*\*)?\s*Answer\s*:\s*(?:\*\*)?\s*(.+)$", re.IGNORECASE)
    for block in split_question_blocks(response):
        match = answer_pattern.search(block)
        if not match:
            continue
        lines = [line.strip() for line in match.group(1).split(";") if line.strip()]
        pairs = {}
        for line in lines:
            if "->" not in line:
                continue
            left, right = line.split("->", 1)
            if left.strip() and right.strip():
                pairs[left.strip()] = right.strip().strip("*")
        question_line = block[:match.start()].strip().splitlines()[0]
        question = re.sub(r"^(?:\*\*)?\d+\.\s*", "", question_line).strip().strip("*")
        if question and pairs:
            questions.append({
                "question": question,
                "options": list(pairs.values()),
                "answer": pairs,
                "question_type": "matching",
            })
    return questions


def build_prompt(

    profession: str,

    question_type: str,

    difficulty_level: str,

    num_questions: int,

    audience_type: str,

    custom_instruction: Optional[str]

) -> str:

    """
    Builds a prompt with all required parameters to generate a well-structured quiz.
    """


    type_formats = {

        "multichoice": """
Each question must have 4 options (A–D), with only one correct answer.
Format Example:
**1. What is the capital of France?**
A) Berlin  
B) Madrid  
C) Paris  
D) Rome  

**Answer:** C
""",

        "true-false": """
For each True/False item:
- Each question must be answerable as "True" or "False" only.
- Ensure the statement is factually correct for the specified topic and timeframe.
- (Optional) Add a 5–10 word justification after the label starting with “Because…”.

Format Example:
**1. The Earth revolves around the Sun.**

**Answer:** True
""",

        "open-ended": """
Each question should require a descriptive response of 1-2 sentences.
Format Example:
**1. Explain the process of photosynthesis.**

**Answer:** Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water.
""",

        "short-answer": """
Each question should require a very short response (1–3 words).
Format Example:
**1. What is the chemical symbol for water?**

**Answer:** H2O
""",

        "matching": """
Each question should ask learners to match 3–5 left-hand prompts to right-hand values.
Put the complete mapping on one answer line, separated by semicolons.
Format Example:
**1. Match each country to its capital.**

**Answer:** France -> Paris; Italy -> Rome; Spain -> Madrid
"""

    }


    custom_part = f"\nAdditional instructions: {custom_instruction}" if custom_instruction else ""


    return f"""
You are generating a **{difficulty_level} difficulty** {question_type} quiz with **{num_questions} questions**.
The quiz topic is **{profession}**, and it is intended for **{audience_type} learners**.

The questions **must strictly follow the format shown below** and must be tailored to the specified topic, audience, and difficulty level.
Ensure every question reflects the topic and context.
Return only the quiz content. Do not include introductions, headings, markdown code fences, separators such as "---", closing commentary, or offers like "let me know if you'd like adjustments".
Every answer must appear only after its own "**Answer:**" marker and never inside the question or option text.

{type_formats.get(question_type, type_formats['multichoice'])}

{custom_part}

Now generate the quiz:
"""


async def resolve_final_token(user_id: Optional[str], provided_token: Optional[str]):

    if provided_token:

        return provided_token


    if user_id:

        saved = await get_user_token(user_id)

        if saved:

            return saved


    return HF_FALLBACK_TOKEN



async def generate_quiz_with_huggingface(payload: Dict[str, Any]) -> Dict[str, Any]:

    loop = asyncio.get_event_loop()


    user_id = payload.get("user_id")

    provided_token = payload.get("token")


    final_token = await resolve_final_token(user_id, provided_token)


    client = InferenceClient(token=final_token)


    response = await loop.run_in_executor(

        None,

        functools.partial(

            client.chat.completions.create,

            model="deepseek-ai/DeepSeek-V3-0324",

            messages=[{

                "role": "user",

                "content": build_prompt(

                    payload.get("profession", "General Knowledge"),

                    payload.get("question_type", "multichoice").lower(),

                    payload.get("difficulty_level", "medium"),

                    int(payload.get("num_questions", 5)),

                    payload.get("audience_type", "general"),

                    payload.get("custom_instruction")

                )

            }],

            max_tokens=2048,

            temperature=0.7,

        ),

    )


    response_text = response.choices[0].message.content


    qtype = payload.get("question_type", "multichoice").lower()


    if qtype == "multichoice":

        questions = parse_multichoice(response_text)

    elif qtype == "true-false":

        questions = parse_true_false(response_text)

    elif qtype == "open-ended":

        questions = parse_open_ended(response_text)

    elif qtype == "short-answer":

        questions = parse_short_answer(response_text)

    elif qtype == "matching":

        questions = parse_matching(response_text)

    else:

        return {"error": f"Unsupported question type: {qtype}"}


    return {

        "questions": questions,

        "raw_response": response_text,

        "source": (

            "temporary_token" if provided_token else

            "user_saved_token" if user_id else

            "default_env"

        )

    }
