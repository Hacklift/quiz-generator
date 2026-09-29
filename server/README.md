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
The backend dependency source of truth is `Pipfile` and `Pipfile.lock`.
Do not treat `server/requirements.txt` as the primary manifest for backend feature work.

```bash
pipenv install
```

### 4. Setup Environment Variables

The project uses `direnv` to manage environment variables from the `.env` file. Ensure you have `direnv` installed and then run:

```bash
direnv allow
```

Start from [server/.env.example](/home/glory/quiz-generator/server/.env.example:1) and provide values for the required variables.

Payment-specific variables:

```plaintext
FRONTEND_BASE_URL=http://localhost:3000
STRIPE_SECRET_KEY=sk_test_replace_me
STRIPE_WEBHOOK_SECRET=whsec_replace_me
STRIPE_PRICE_ID_MONTHLY=price_replace_monthly
STRIPE_PRICE_ID_YEARLY=price_replace_yearly
```

For document-based quiz generation with RAG, configure:

```plaintext
HUGGINGFACEHUB_API_TOKEN=hf_replace_with_your_token
```

The remaining document quiz model and chunking settings already have defaults in
[server/app/core/config.py](/home/glory/quiz-generator/server/app/core/config.py:25).
Only add them to `.env` when you need to override those defaults for a specific environment.

The remaining document quiz model and chunking settings already have defaults in
[server/app/core/config.py](/home/glory/quiz-generator/server/app/core/config.py:25).
Only add them to `.env` when you need to override those defaults for a specific environment.

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
