from pydantic import BaseModel

from typing import Union


class UserAnswer(BaseModel):

    question: str

    user_answer: Union[str, int]

    correct_answer: Union[str, int]

    question_type: str

