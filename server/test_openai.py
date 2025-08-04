import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # Loads .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # ✅ Changed from "gpt-4" to "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What's 3 + 5?"}
        ],
        temperature=0.7
    )

    print("✅ Response from OpenAI:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ OpenAI call failed:")
    print(e)
