import json
import logging
from typing import Any

from server.app.assistant.providers import GeminiProvider, GroqProvider
from server.app.core.config import settings
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService


logger = logging.getLogger(__name__)


OPEN_RESPONSE_TYPES = {"short-answer", "open-ended"}


class QuizAnswerKeyService:
    def __init__(self, *, library_service: QuizUserLibraryService | None = None):
        self.library_service = library_service or QuizUserLibraryService()

    @staticmethod
    def _quiz_type(quiz: QuizDocumentV2) -> str:
        return quiz.quiz_type.value if hasattr(quiz.quiz_type, "value") else str(quiz.quiz_type)

    @staticmethod
    def _stored_answer_items(quiz: QuizDocumentV2) -> list[dict[str, Any]]:
        return [
            {
                "question_number": index,
                "question": question.question,
                "answer": question.correct_answer,
                "stored_answer": question.correct_answer,
                "options": question.options,
                "source": "stored",
            }
            for index, question in enumerate(quiz.questions, start=1)
        ]

    def _build_answer_guidance_prompt(self, quiz: QuizDocumentV2) -> str:
        questions = [
            {
                "question_number": index,
                "question": question.question,
                "stored_answer": question.correct_answer,
            }
            for index, question in enumerate(quiz.questions, start=1)
        ]
        return (
            "Return raw JSON only. Build a concise answer key for this quiz. "
            "For short-answer questions, answers should usually be 1-5 words. "
            "For open-ended questions, answers should be 1-3 clear sentences. "
            "Use the stored answer as ground truth when it is adequate, but improve clarity where useful. "
            "Schema: {\"answers\":[{\"question_number\":number,\"answer\":\"string\"}]}.\n"
            f"Quiz title: {quiz.title}\n"
            f"Quiz type: {self._quiz_type(quiz)}\n"
            f"Questions: {json.dumps(questions, ensure_ascii=True, default=str)}"
        )

    def _build_provider(self):
        provider_name = settings.ASSISTANT_EXECUTOR_PROVIDER.lower().strip()
        if provider_name == "gemini":
            return GeminiProvider(settings.GEMINI_API_KEY)
        if provider_name == "groq":
            return GroqProvider(settings.GROQ_API_KEY)
        raise ValueError(f"Unsupported answer-key provider: {settings.ASSISTANT_EXECUTOR_PROVIDER}")

    @staticmethod
    def _parse_json_payload(raw_response: str) -> dict[str, Any]:
        payload = raw_response.strip()
        if payload.startswith("```"):
            lines = payload.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            payload = "\n".join(lines).strip()
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}

    async def _generate_open_response_answers(self, quiz: QuizDocumentV2) -> dict[int, str]:
        provider = self._build_provider()
        raw_response = await provider.generate(
            model=settings.ASSISTANT_EXECUTOR_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON in message content.",
                },
                {
                    "role": "user",
                    "content": self._build_answer_guidance_prompt(quiz),
                },
            ],
            temperature=0,
        )
        payload = self._parse_json_payload(raw_response)
        answers = payload.get("answers") if isinstance(payload, dict) else None
        if not isinstance(answers, list):
            return {}
        generated: dict[int, str] = {}
        for answer in answers:
            if not isinstance(answer, dict):
                continue
            try:
                question_number = int(answer.get("question_number"))
            except (TypeError, ValueError):
                continue
            text = str(answer.get("answer") or "").strip()
            if text:
                generated[question_number] = text
        return generated

    async def get_answer_key(
        self,
        *,
        user_id: str,
        quiz_id: str,
    ) -> dict[str, Any]:
        quiz = await self.library_service.get_owned_or_library_quiz(
            user_id=user_id,
            quiz_id=quiz_id,
        )
        if quiz is None:
            raise ValueError("Quiz not found or not available in your library.")

        quiz_type = self._quiz_type(quiz)
        items = self._stored_answer_items(quiz)
        model_generated = False
        model_warning = None

        if quiz_type in OPEN_RESPONSE_TYPES:
            try:
                generated_answers = await self._generate_open_response_answers(quiz)
                if generated_answers:
                    model_generated = True
                    for item in items:
                        generated_answer = generated_answers.get(item["question_number"])
                        if generated_answer:
                            item["answer"] = generated_answer
                            item["source"] = "model_generated"
            except Exception as exc:
                model_warning = "Model-generated answer guidance is unavailable; using stored answers."
                logger.warning("answer key model guidance failed: %s", exc)

        return {
            "quiz_id": str(quiz.id),
            "title": quiz.title,
            "question_type": quiz_type,
            "answer_count": len(items),
            "model_generated": model_generated,
            "model_warning": model_warning,
            "answers": items,
        }
