---
name: run-tests
description: Workflow for running backend pytest test suites and frontend Jest unit tests with proper environment configurations.
---

# Run Tests Skill

Follow this workflow to execute tests across the backend and frontend.

## 1. Running Backend Tests (FastAPI / Pytest)

Backend tests reside in `server/tests/`.

### Run All Backend Tests:
```bash
cd server
pytest
```

### Run Specific Test File or Directory:
```bash
# Run auth test suite
pytest server/tests/test_auth.py

# Run RAG & quiz generation tests
pytest server/tests/test_document_quiz.py
```

### Environment Requirements for Backend Tests:
- `pytest` uses `asyncio` for testing async FastAPI routes.
- Ensure test DB configuration points to local/mocked instances or test databases.

---

## 2. Running Frontend Tests (Next.js / Jest)

Frontend tests reside in `client/__tests__/` or next to feature components.

### Run All Frontend Tests:
```bash
cd client
pnpm test
```

### Run Targeted Test File:
```bash
cd client
pnpm test __tests__/QuizwerkHomePage.test.tsx
```

### Type Check & Code Quality Verification:
```bash
cd client
pnpm exec tsc --noEmit
pnpm lint
```

---

## 3. Best Practices for Writing New Tests
- **Backend**: Mock external LLM calls (OpenAI, Gemini, Groq) and SMTP email dispatches during route testing.
- **Frontend**: Use `@testing-library/react` and mock Next.js `useRouter` hooks and Axios requests.
