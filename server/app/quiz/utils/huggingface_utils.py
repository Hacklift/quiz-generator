import json
import os
import re
from typing import Any, Dict, List, Union
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

client = InferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))

def clean_and_extract_questions(response: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Extracts multiple-choice questions from the model's response.
    Expected format:
        **1. Question text**
        A) Option A  
        B) Option B  
        C) Option C  
        D) Option D  

        **Answer:** A
    """
    try:
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

            questions.append({
                "question": question_text.strip(),
                "options": formatted_options,
                "answer": correct_letter.strip()
            })

        return questions

    except Exception:
        return {"error": "Invalid format or unexpected output", "raw": response}

def generate_quiz_with_huggingface(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a multiple-choice quiz using a HuggingFace model.
    """
   
    profession = payload.get("profession", "biology")
    question_type = payload.get("question_type", "multichoice")
    difficulty_level = payload.get("difficulty_level", "hard")
    num_questions = int(payload.get("num_questions", 4))

    prompt = f"""
    Generate a {difficulty_level} difficulty {question_type} quiz with {num_questions} questions on {profession}.
    Each question should be clearly numbered and provide options A–D, with the correct answer stated after each question.
    Format:
    **1. Question here**
    A) Option A  
    B) Option B  
    C) Option C  
    D) Option D  

    **Answer:** A
    """

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3-0324",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.7
    )

    response_text = response.choices[0].message.content
    questions = clean_and_extract_questions(response_text)

    return {
        "message": "Quiz generated successfully",
        "profession": profession,
        "num_questions": num_questions,
        "question_type": question_type,
        "difficulty_level": difficulty_level,
        "questions": questions
    }
