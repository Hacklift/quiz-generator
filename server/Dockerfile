FROM python:3.12-slim

WORKDIR /server

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    pip install --no-cache-dir --upgrade pip pipenv && \
    rm -rf /var/lib/apt/lists/*

COPY Pipfile Pipfile.lock ./

RUN pipenv install --system --skip-lock

COPY . .

EXPOSE 10000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "10000"]
