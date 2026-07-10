from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService


def _find_folder_quiz_item(folder: dict | None, folder_item_id: str) -> dict | None:
    for item in (folder or {}).get("quizzes", []):
        if item.get("id") == folder_item_id or item.get("folder_item_id") == folder_item_id:
            return item
    return None


def _folder_name(folder: dict | None) -> str | None:
    return folder.get("name") if folder else None


async def folder_list() -> list[dict]:
    context = await get_mcp_request_context(require_auth=True)
    return await QuizUserLibraryService().list_folders(user_id=context.user_id)


async def folder_get(folder_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    folder = await QuizUserLibraryService().get_folder(
        folder_id=folder_id,
        user_id=context.user_id,
    )
    if folder is None:
        return {
            "found": False,
            "folder_id": folder_id,
            "id": None,
            "name": None,
            "quizzes": [],
        }
    return {"found": True, "folder_id": folder.get("id"), **folder}


async def folder_get_by_name(name: str) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    folder = await QuizUserLibraryService().get_folder_by_name(
        user_id=context.user_id,
        name=name,
    )
    if folder is None:
        return {
            "found": False,
            "folder_id": None,
            "id": None,
            "name": name,
            "quizzes": [],
        }
    return {"found": True, "folder_id": folder.get("id"), **folder}


async def folder_find_quiz_by_title(title: str) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    return await QuizUserLibraryService().find_quiz_in_folders_by_title(
        user_id=context.user_id,
        title=title,
    )


async def folder_create(name: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    folder = await QuizUserLibraryService().create_folder(
        user_id=context.user_id,
        name=name,
    )
    return {
        "id": str(folder.id),
        "folder_id": str(folder.id),
        "user_id": folder.user_id,
        "name": folder.name,
        "created_at": folder.created_at.isoformat(),
        "updated_at": folder.updated_at.isoformat(),
    }


async def folder_add_saved_quiz(folder_id: str, saved_quiz_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    folder, item = await QuizUserLibraryService().add_saved_quiz_to_folder(
        folder_id=folder_id,
        saved_quiz_id=saved_quiz_id,
        user_id=context.user_id,
    )
    return {
        "id": str(item.id),
        "folder_item_id": str(item.id),
        "folder_id": item.folder_id,
        "quiz_id": item.quiz_id,
        "saved_quiz_id": saved_quiz_id,
        "title": item.display_title,
        "folder_name": folder.name,
        "created_at": item.created_at.isoformat(),
    }


async def folder_rename(folder_id: str, new_name: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    folder = await QuizUserLibraryService().rename_folder(
        folder_id=folder_id,
        user_id=context.user_id,
        new_name=new_name,
    )
    if folder is None:
        raise ValueError("Folder not found")
    return {
        "id": str(folder.id),
        "folder_id": str(folder.id),
        "name": folder.name,
        "updated_at": folder.updated_at.isoformat(),
    }


async def folder_delete(folder_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    service = QuizUserLibraryService()
    folder = await service.get_folder(folder_id=folder_id, user_id=context.user_id)
    deleted = await service.delete_folder(
        folder_id=folder_id,
        user_id=context.user_id,
    )
    if not deleted:
        raise ValueError("Folder not found")
    return {
        "message": "Folder deleted.",
        "folder_id": folder_id,
        "folder_name": _folder_name(folder),
        "deleted": True,
    }


async def folder_remove_quiz(folder_id: str, folder_item_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    service = QuizUserLibraryService()
    folder = await service.get_folder(folder_id=folder_id, user_id=context.user_id)
    quiz_item = _find_folder_quiz_item(folder, folder_item_id)
    removed = await service.remove_folder_item(
        folder_id=folder_id,
        folder_item_id=folder_item_id,
        user_id=context.user_id,
    )
    if not removed:
        raise ValueError("Folder quiz item not found")
    return {
        "message": "Quiz removed from folder.",
        "folder_id": folder_id,
        "folder_name": _folder_name(folder),
        "folder_item_id": folder_item_id,
        "title": quiz_item.get("title") if quiz_item else None,
        "removed": True,
    }


async def folder_move_quiz(folder_item_id: str, source_folder_id: str, target_folder_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    service = QuizUserLibraryService()
    source_folder = await service.get_folder(folder_id=source_folder_id, user_id=context.user_id)
    target_folder = await service.get_folder(folder_id=target_folder_id, user_id=context.user_id)
    quiz_item = _find_folder_quiz_item(source_folder, folder_item_id)
    moved = await service.move_folder_item(
        folder_item_id=folder_item_id,
        source_folder_id=source_folder_id,
        target_folder_id=target_folder_id,
        user_id=context.user_id,
    )
    if not moved:
        raise ValueError("Folder quiz item not found")
    return {
        "message": "Quiz moved between folders.",
        "folder_item_id": folder_item_id,
        "source_folder_id": source_folder_id,
        "target_folder_id": target_folder_id,
        "source_folder_name": _folder_name(source_folder),
        "target_folder_name": _folder_name(target_folder),
        "title": quiz_item.get("title") if quiz_item else None,
        "quiz_id": quiz_item.get("quiz_id") if quiz_item else None,
        "moved": True,
    }
