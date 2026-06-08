# Testing Guide

## Overview

This project includes both backend and frontend test suites to help ensure application stability and reliability.

### Testing Frameworks

| Layer    | Framework                   |
| -------- | --------------------------- |
| Backend  | Pytest, Pytest-Asyncio      |
| Frontend | Jest, React Testing Library |

---

## Backend Testing

### Prerequisites

Install project dependencies using Pipenv:

```bash
cd server

pip install pipenv

pipenv install

pipenv shell
```

### Running Backend Tests

Run all backend tests:

```bash
pytest
```

Run a specific test file:

```bash
pytest tests/test_quiz.py
```

Run tests with verbose output:

```bash
pytest -v
```

### Backend Test Dependencies

Testing dependencies are defined in `server/Pipfile`.

Current testing packages include:

```text
pytest
pytest-asyncio
```

### Current Known Issues

Some backend tests may fail if required dependencies are not installed.

Common missing dependencies include:

* pydantic
* fastapi
* bson
* huggingface_hub
* openai

Ensure all project dependencies are installed before running tests.

---

## Frontend Testing

### Prerequisites

Install frontend dependencies:

```bash
cd client

pnpm install
```

### Running Frontend Tests

Run all frontend tests:

```bash
pnpm test
```

Or:

```bash
npm test
```

### Watch Mode

Run tests continuously during development:

```bash
pnpm test:watch
```

Or:

```bash
npm run test:watch
```

### Frontend Testing Stack

The frontend uses:

* Jest
* React Testing Library
* @testing-library/jest-dom
* @testing-library/user-event

### Current Known Issues

At the time of writing:

* One frontend test suite is currently passing.
* Several test suites fail due to outdated import paths.

Recommended actions:

1. Update outdated import paths.
2. Verify component locations and exports.
3. Re-run the test suite.

---

## Test Coverage

### Frontend Coverage

Jest supports coverage reporting.

Generate a coverage report using:

```bash
pnpm test -- --coverage
```

Or:

```bash
npx jest --coverage
```

Coverage results will be generated inside:

```text
client/coverage/
```

### Backend Coverage

Backend coverage reporting is not currently configured.

Recommended future setup:

```bash
pip install pytest-cov
```

Run coverage reporting:

```bash
pytest --cov=app
```

Future improvements should include:

* Adding `pytest-cov` to project dependencies
* Generating coverage reports automatically
* Enforcing minimum coverage thresholds

---

## Test Locations

### Backend

Backend tests are located in:

```text
server/tests/
```

Example test files include:

```text
test_quiz.py
email_tests/
v2_database_tests/
```

### Frontend

Frontend tests follow standard Jest naming conventions:

```text
*.test.ts
*.test.tsx
```

and are currently in client/__tests__/ (may move alongside components in the future)

---

## Recommended Workflow

Before opening a pull request:

### Backend

```bash
cd server

pytest
```

### Frontend

```bash
cd client

pnpm test
```

Resolve all failing tests before submitting changes for review.

---

## Future Improvements

* Configure backend coverage reporting using `pytest-cov`
* Add frontend coverage thresholds
* Run tests automatically in CI/CD pipelines
* Generate coverage reports on every pull request
* Publish coverage metrics for contributors
* Improve and expand existing test coverage

```
```
