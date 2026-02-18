import csv

from io import StringIO

from typing import List



def generate_csv(data: List[dict]):

    buffer = StringIO()

    writer = csv.writer(buffer)

    writer.writerow(["Question", "Options", "Answer"])

    for item in data:

        options = ", ".join(item.get("options", []))

        writer.writerow([item["question"], options, item["answer"]])

    buffer.seek(0)

    return buffer

