from fastapi import APIRouter, Depends, Request

from server.app.assistant.schemas import AssistantChatRequest, AssistantChatResponse
from server.app.assistant.service import AssistantService
from server.app.core.dependencies import get_current_user_optional
from server.app.users.models import UserOut


router = APIRouter()


@router.post("/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    payload: AssistantChatRequest,
    request: Request,
    current_user: UserOut | None = Depends(get_current_user_optional),
) -> AssistantChatResponse:
    authorization_header = request.headers.get("authorization")
    return await AssistantService().chat(
        request=payload,
        user=current_user,
        authorization_header=authorization_header,
    )
