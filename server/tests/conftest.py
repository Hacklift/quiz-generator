import os

pytest_plugins = ["pytest_asyncio"]

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("SENDER_EMAIL", "test-sender@example.com")
os.environ.setdefault("SENDER_PASSWORD", "test-password")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("SHARE_URL", "http://localhost:3000")
os.environ.setdefault("DB_NAME", "quiz_generator_test")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
