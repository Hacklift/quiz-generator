import inspect
from fastapi.params import Depends as DependsClass
from server.app.db.routes.saved_quizzes import remove_saved_quiz
from server.app.auth.dependencies import get_current_user


def test_remove_saved_quiz_requires_auth_dependency():
    sig = inspect.signature(remove_saved_quiz)
    param = sig.parameters["current_user"]
    assert isinstance(param.default, DependsClass)
    assert param.default.dependency == get_current_user
