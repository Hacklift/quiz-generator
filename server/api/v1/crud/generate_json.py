import json
from io import StringIO
from typing import Any


def generate_json(payload: dict[str, Any]):
    buffer = StringIO()
    json.dump(payload, buffer, indent=2, ensure_ascii=True)
    buffer.seek(0)
    return buffer
