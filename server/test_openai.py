import os

import pytest

from openai import OpenAI

from dotenv import load_dotenv


load_dotenv()


api_key = os.getenv("OPENAI_API_KEY")

if not api_key:

    pytest.skip(

        "OPENAI_API_KEY is not set; skipping OpenAI integration test.",

        allow_module_level=True,

    )


client = OpenAI(api_key=api_key)


def test_openai_chat_completion():

    response = client.chat.completions.create(

        model="gpt-3.5-turbo",

        messages=[

            {"role": "system", "content": "You are a helpful assistant."},

            {"role": "user", "content": "What's 3 + 5?"},

        ],

        temperature=0.7,

    )


    assert response.choices[0].message.content

