from server.app.mcp.tools.folder_tools import folder_get, folder_list
from server.app.mcp.tools.library_tools import (
    library_get_history_detail,
    library_list_history,
    library_list_saved_quizzes,
)


async def saved_quizzes_resource() -> dict:
    return {"saved_quizzes": await library_list_saved_quizzes()}


async def quiz_history_resource() -> dict:
    return {"history": await library_list_history()}


async def quiz_history_detail_resource(history_id: str) -> dict:
    return {"history_item": await library_get_history_detail(history_id)}


async def folders_resource() -> dict:
    return {"folders": await folder_list()}


async def folder_resource(folder_id: str) -> dict:
    return {"folder": await folder_get(folder_id)}
