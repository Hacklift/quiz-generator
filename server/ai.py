import os

import re

import json

from huggingface_hub import InferenceClient

from dotenv import load_dotenv



load_dotenv()


def generate_quiz_json():

    token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

    client = InferenceClient(token=token)

    completion = client.chat.completions.create(

        model="deepseek-ai/DeepSeek-V3-0324",

        messages=[{

            "role": "user",

            "content": (

                "Generate 4 quiz question about Lion. Each question should have 4 "

                "options and the correct answer should be the last option. "

                "The questions should be in JSON format with the following structure: "

                "{\"question\": \"\", \"options\": [\"\", \"\", \"\", \"\"], \"answer\": \"\"}."

            ),

        }],

    )


    raw = completion.choices[0].message.content



    m = re.search(r"```json\s*(\[\s*{.*}\s*\])\s*```", raw, re.DOTALL)

    json_text = m.group(1) if m else raw



    try:

        quiz = json.loads(json_text)

    except json.JSONDecodeError as e:

        raise ValueError(f"Failed to parse JSON from model output: {e}\n\nOutput was:\n{raw}")



    print(json.dumps(quiz, indent=2))


if __name__ == "__main__":

    generate_quiz_json()
