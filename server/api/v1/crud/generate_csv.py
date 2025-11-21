import csv
from io import StringIO
from typing import List


def generate_csv(data: List[dict]):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Question", "Options", "Answer"])

    for item in data:
        raw_options = item.get("options")

        if isinstance(raw_options, list):
            options = ", ".join(raw_options)
        else:
            options = ""

        writer.writerow([item["question"], options, item["answer"]])

    buffer.seek(0)
    return buffer

