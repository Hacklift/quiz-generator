from typing import List, Optional


from pydantic import BaseModel


class QuizQuestionsModel(BaseModel):

    question: str

    options: Optional[List[str]]

    answer: str

