import os
import re
import asyncio
import functools
from typing import Any, Dict, List, Optional
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from ....app.db.crud.token_crud import get_user_token

load_dotenv()
HF_FALLBACK_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# =====================================================
# =============== PARSING FUNCTIONS ===================
# =====================================================

def parse_multichoice(response: str) -> List[Dict[str, Any]]:
    """Parse multiple-choice questions with A–D options."""
    question_blocks = re.findall(
        r"\*\*\d+\.\s*(.*?)\*\*\s*(.*?)\n+\*\*Answer:\*\*\s*([A-D])",
        response,
        re.DOTALL
    )

    questions = []
    for question_text, options_block, correct_letter in question_blocks:
        # Find options A-D
        options = re.findall(r"([A-D]\))\s*(.*?)\s{2,}", options_block + "  ", re.DOTALL)
        if not options:
            options = re.findall(r"([A-D]\))\s*(.*?)\n", options_block)

        formatted_options = [f"{opt[0]} {opt[1].strip()}" for opt in options]

        # Convert "A"/"B"/"C"/"D" into the actual text
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
    """Parse true/false questions."""
    question_blocks = re.findall(
        r"\*\*\d+\.\s*(.*?)\*\*\s*\n+\*\*Answer:\*\*\s*(True|False)",
        response,
        re.IGNORECASE | re.DOTALL
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
    """Parse open-ended questions requiring longer answers."""
    question_blocks = re.findall(
        r"\*\*\d+\.\s*(.*?)\*\*\s*\n+\*\*Answer:\*\*\s*(.+?)(?=\n\*\*|$)",
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
    """Parse short-answer questions requiring 1–3 words."""
    return [
        {**item, "question_type": "short-answer"}
        for item in parse_open_ended(response)
    ]

# =====================================================
# ================= PROMPT BUILDER ====================
# =====================================================

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

    # Strict format instructions for each type
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
"""
    }

    # Include extra custom instruction if provided
    custom_part = f"\nAdditional instructions: {custom_instruction}" if custom_instruction else ""

    # Full prompt
    return f"""
You are generating a **{difficulty_level} difficulty** {question_type} quiz with **{num_questions} questions**.
The quiz topic is **{profession}**, and it is intended for **{audience_type} learners**.

The questions **must strictly follow the format shown below** and must be tailored to the specified topic, audience, and difficulty level.
Ensure every question reflects the topic and context.

{type_formats.get(question_type, type_formats['multichoice'])}

{custom_part}

Now generate the quiz:
"""

# =====================================================
# ================= MAIN FUNCTION =====================
# =====================================================

async def generate_quiz_with_huggingface(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async wrapper for HuggingFace call.
    """
    loop = asyncio.get_event_loop()

    # 1. Get token from DB (for dev, hardcode user_id)
    user_id = "dev_user"  # TODO: replace with real auth later
    user_token = await get_user_token(user_id)

    request_token = (payload.get("token") or "").strip() or None
    
    final_token = request_token or user_token or HF_FALLBACK_TOKEN

    # 3. Build client with the chosen token
    client = InferenceClient(token=final_token)

    # 4. Run HuggingFace call
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
                    payload.get("custom_instruction"),
                )
            }],
            max_tokens=2048,
            temperature=0.7,
        ),
    )

    response_text = response.choices[0].message.content
    print("\n--- Raw Model Response ---\n", response_text, "\n--------------------------\n")

    # 5. Parse response
    qtype = payload.get("question_type", "multichoice").lower()
    if qtype == "multichoice":
        questions = parse_multichoice(response_text)
    elif qtype == "true-false":
        questions = parse_true_false(response_text)
    elif qtype == "open-ended":
        questions = parse_open_ended(response_text)
    elif qtype == "short-answer":
        questions = parse_short_answer(response_text)
    else:
        return {"error": f"Unsupported question type: {qtype}", "raw": response_text}

    return {
        "message": "Quiz generated successfully",
        "questions": questions,
        "raw_response": response_text,
        "source": "user_token" if user_token else "default_env",  # 👈 helpful metadata
        **payload,
    }
