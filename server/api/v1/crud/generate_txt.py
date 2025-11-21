from io import StringIO
from typing import List


def generate_txt(data: List[dict]):
    buffer = StringIO()
    for item in data:
        buffer.write(f"Question: {item['question']}\n")
        if (item.get("options") or "").strip():
            buffer.write("Options: " + ", ".join(item['options']) + "\n")
        buffer.write(f"Answer: {item['answer']}\n\n")
    buffer.seek(0)
    return buffer
