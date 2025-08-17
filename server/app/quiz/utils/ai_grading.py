from fastapi import HTTPException
from huggingface_hub import InferenceClient
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
if not HUGGINGFACE_API_TOKEN:
    raise RuntimeError("HUGGINGFACEHUB_API_TOKEN is not set in .env")

client = InferenceClient(
    model="deepseek-ai/DeepSeek-V3-0324",
    token=HUGGINGFACE_API_TOKEN
)


def normalize_answer(ans: str):
    return ans.strip().lower()


def grade_with_ai(user_answers):
    try:
        prompt = format_ai_grading_prompt(user_answers)

        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
        )

        response_text = response.choices[0].message.content.strip()

        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n|\n```$", "", response_text.strip(), flags=re.IGNORECASE)

        try:
            graded_result = json.loads(response_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"AI response is not valid JSON:\n{response_text}")

        # ✅ Override is_correct manually for multichoice and true-false
        for i, result in enumerate(graded_result):
            qtype = user_answers[i].get("question_type", "").lower()
            ua = normalize_answer(user_answers[i]["user_answer"])
            ca = normalize_answer(user_answers[i]["correct_answer"])

            if qtype in ["multichoice", "true-false"]:
                result["is_correct"] = ua == ca

                # Optional feedback override
                if not result.get("feedback"):
                    result["feedback"] = (
                        "Exact match confirmed." if result["is_correct"]
                        else f"Expected '{user_answers[i]['correct_answer']}', but got '{user_answers[i]['user_answer']}'."
                    )

        return graded_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI grading failed: {str(e)}")
