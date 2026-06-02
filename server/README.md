# Quiz Generator App Server

This directory contains the backend code for the Quiz App, built using Python FastAPI. The backend handles the API endpoints, including health checks, and serves as the core engine for the application's logic.

## Requirements

- **Python**: 3.12
- **pipenv**: For managing Python dependencies.
- **direnv**: For managing environment variables with the `.env` file.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/quiz-app.git
cd quiz-generator/server
```

### 2. Create virtual enviroment

Ensure you are in the server directory then run the following command

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

Ensure you have Python 3.12 installed. Then, install the required dependencies using `pipenv`.

```bash
pipenv install
```

### 4. Setup Environment Variables

The project uses `direnv` to manage environment variables from the `.env` file. Ensure you have `direnv` installed and then run:

```bash
direnv allow
```

Start from [server/.env.example](/home/glory/quiz-generator/server/.env.example:1) and provide values for the required variables.

For document-based quiz generation with RAG, configure:

```plaintext
HUGGINGFACEHUB_API_TOKEN=hf_replace_with_your_token
HF_QUIZ_MODEL=Qwen/Qwen2.5-7B-Instruct
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
DOCUMENT_UPLOAD_MAX_BYTES=10485760
DOCUMENT_RAG_MAX_CHUNKS=24
DOCUMENT_RAG_TOP_K=8
```

### 5. Run the Application

Start the FastAPI server with the following command:

```bash
pipenv run fastapi dev main.py
```

The API will be accessible at `http://localhost:8000/api`.

### 6. Access Healthcheck

Verify the API is running correctly by visiting the health check endpoint:

```bash
http://localhost:8000/api/healthcheck
```

You should receive a JSON response confirming the server is up and running.
