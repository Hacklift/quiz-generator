from __future__ import annotations

from typing import Any

from server.app.assistant.schemas import AssistantArtifact, ToolResult
from server.app.assistant.outcomes import project_tool_outcomes
from server.app.assistant.response_presenter import outcome_artifact_label
from server.app.quiz.services.category_taxonomy_service import slugify


WRITE_TOOLS = {
    "folder_add_saved_quiz",
    "folder_create",
    "folder_delete",
    "folder_move_quiz",
    "folder_remove_quiz",
    "folder_rename",
    "library_save_quiz",
    "live_quiz_create_access_link",
    "live_quiz_send_invites",
    "saved_quiz_delete",
    "saved_quiz_rename",
    "share_send_email",
}

LOOKUP_ARTIFACT_TOOLS = {
    "folder_find_quiz_by_title",
    "folder_get",
    "folder_get_by_name",
    "folder_list",
    "library_get_history_detail",
    "library_get_saved_quiz",
    "library_list_history",
    "library_list_saved_quizzes",
    "share_get_quiz",
}


def _items_from_result(data: Any) -> list[dict[str, Any]]:
    items = data.get("result") if isinstance(data, dict) and "result" in data else data
    return items if isinstance(items, list) else []


def _resource_list_artifact(
    *,
    resource: str,
    title: str,
    items: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> AssistantArtifact:
    return AssistantArtifact(
        type="resource_list",
        data={
            "resource": resource,
            "title": title,
            "items": items,
            "metadata": metadata or {},
            "pagination": {
                "shown": len(items),
                "total": len(items),
                "has_more": False,
            },
        },
    )


def _folder_display_title(folder_name: Any) -> str:
    name = str(folder_name or "Folder").strip() or "Folder"
    return name if name.casefold().endswith(" folder") else f"{name} Folder"


def _resource_artifact(
    *,
    resource: str,
    label: str,
    href: str | None = None,
    metadata: dict[str, Any] | None = None,
    actions: list[dict[str, Any]] | None = None,
) -> AssistantArtifact:
    return AssistantArtifact(
        type="resource",
        data={
            "resource": resource,
            "label": label,
            "href": href,
            "metadata": metadata or {},
            "actions": actions or [],
        },
    )


def _status_artifact(
    *,
    resource: str,
    label: str,
    metadata: dict[str, Any],
) -> AssistantArtifact:
    return AssistantArtifact(
        type="status",
        data={
            "resource": resource,
            "label": label,
            "metadata": metadata,
        },
    )


def infer_artifacts_from_results(
    results: list[ToolResult],
    *,
    suppress_internal_lookup: bool = False,
    suppress_final_status_tools: set[str] | None = None,
    page_context: dict[str, Any] | None = None,
    recent_artifacts: list[dict[str, Any]] | None = None,
) -> list[AssistantArtifact]:
    artifacts: list[AssistantArtifact] = []
    outcomes = {
        outcome.step_id: outcome
        for outcome in project_tool_outcomes(
            results,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
    }
    has_write_result = any(result.tool_name in WRITE_TOOLS for result in results)
    final_result = results[-1] if results else None
    suppress_final_status_tools = suppress_final_status_tools or set()

    for result in results:
        if not result.ok:
            continue
        if result.tool_name == "library_find_saved_quiz_by_title":
            continue
        if (
            suppress_internal_lookup
            and has_write_result
            and result.tool_name in LOOKUP_ARTIFACT_TOOLS
        ):
            continue

        data = result.data

        if result.tool_name == "category_list":
            categories = _items_from_result(data)
            items = [
                {
                    "id": slugify(str(category)),
                    "label": str(category),
                    "href": f"/categories/{slugify(str(category))}",
                    "metadata": {"category": str(category)},
                }
                for category in categories
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="category",
                    title="Quiz Categories",
                    items=items,
                )
            )

        if result.tool_name == "category_list_subcategories":
            subcategories = _items_from_result(data)
            category = str(data.get("category") or "") if isinstance(data, dict) else ""
            category_slug = slugify(category) if category else None
            items = [
                {
                    "id": slugify(str(subcategory)),
                    "label": str(subcategory),
                    "href": (
                        f"/categories/{category_slug}/{slugify(str(subcategory))}"
                        if category_slug
                        else "/categories"
                    ),
                    "metadata": {"category": category, "subcategory": str(subcategory)},
                }
                for subcategory in subcategories
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="subcategory",
                    title=f"{category} Subcategories" if category else "Subcategories",
                    items=items,
                )
            )

        if result.tool_name == "category_browse_questions":
            questions = _items_from_result(data)
            items = [
                {
                    "id": str(index),
                    "label": str(question.get("question") or "Category question"),
                    "metadata": question,
                }
                for index, question in enumerate(questions, start=1)
                if isinstance(question, dict)
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="category_question",
                    title="Category Questions",
                    items=items,
                )
            )

        if result.tool_name == "quiz_generate":
            quiz_data = {
                "quiz_id": data.get("quiz_id"),
                "history_id": data.get("history_id"),
                "title": data.get("title"),
                "question_type": data.get("question_type"),
                "question_count": data.get("question_count"),
                "questions": data.get("questions") or [],
            }
            artifacts.append(
                _resource_artifact(
                    resource="quiz",
                    label=str(data.get("title") or "Generated quiz"),
                    href=(
                        f"/quiz_display?quizId={data.get('quiz_id')}&questionType={data.get('question_type') or 'multichoice'}"
                        if data.get("quiz_id")
                        else None
                    ),
                    metadata=quiz_data,
                )
            )

        if result.tool_name == "quiz_get_answers":
            answers = data.get("answers")
            if isinstance(answers, list):
                outcome = outcomes[result.step_id]
                display_title = outcome.subject.title if outcome.subject else str(data.get("title") or "Quiz")
                items = [
                    {
                        "id": str(item.get("question_number") or index),
                        "label": (
                            f"{item.get('question_number') or index}. "
                            f"{item.get('question') or 'Question'} - {item.get('answer') or 'No answer'}"
                        ),
                        "metadata": item,
                    }
                    for index, item in enumerate(answers, start=1)
                    if isinstance(item, dict)
                ]
                artifacts.append(
                    _resource_list_artifact(
                        resource="quiz_answer",
                        title=f"Answer Key: {display_title}",
                        items=items,
                        metadata={
                            "quiz_id": data.get("quiz_id"),
                            "title": display_title,
                            "display_title": display_title,
                            "canonical_title": data.get("title"),
                            "question_type": data.get("question_type"),
                            "answer_count": data.get("answer_count"),
                        },
                    )
                )

        if result.tool_name == "library_list_saved_quizzes":
            saved_items = [
                {
                    "id": item.get("id") or item.get("_id"),
                    "quiz_id": item.get("quiz_id"),
                    "title": item.get("title") or "Saved quiz",
                    "question_type": item.get("question_type"),
                }
                for item in _items_from_result(data)
                if isinstance(item, dict)
            ]
            generic_items = [
                {
                    "id": item["id"],
                    "label": item["title"],
                    "href": (
                        f"/quiz_display?savedId={item['id']}&quizId={item.get('quiz_id') or item['id']}"
                        f"&questionType={item.get('question_type') or 'multichoice'}"
                    ),
                    "metadata": item,
                }
                for item in saved_items
                if item.get("id")
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="saved_quiz",
                    title="Saved Quizzes",
                    items=generic_items,
                )
            )

        if result.tool_name == "library_list_history":
            history_items = [
                {
                    "id": item.get("id") or item.get("_id"),
                    "quiz_id": item.get("quiz_id"),
                    "title": item.get("quiz_name") or item.get("title") or "Quiz history",
                    "question_type": item.get("question_type"),
                }
                for item in _items_from_result(data)
                if isinstance(item, dict)
            ]
            generic_items = [
                {
                    "id": item["id"],
                    "label": item["title"],
                    "href": f"/quiz_history/{item['id']}",
                    "metadata": item,
                }
                for item in history_items
                if item.get("id")
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="quiz_history",
                    title="Quiz History",
                    items=generic_items,
                )
            )

        if result.tool_name == "folder_list":
            folder_items = [
                {
                    "id": item.get("id") or item.get("_id"),
                    "name": item.get("name") or "Folder",
                    "quiz_count": item.get("quiz_count"),
                }
                for item in _items_from_result(data)
                if isinstance(item, dict)
            ]
            generic_items = [
                {
                    "id": item["id"],
                    "label": item["name"],
                    "href": f"/folders/{item['id']}",
                    "metadata": item,
                }
                for item in folder_items
                if item.get("id")
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="folder",
                    title="Folders",
                    items=generic_items,
                )
            )

        if result.tool_name == "folder_get_by_name":
            quizzes = data.get("quizzes")
            if isinstance(quizzes, list):
                folder_name = data.get("name") or "Folder"
                folder_display_title = _folder_display_title(folder_name)
                folder_items = [
                    {
                        "id": item.get("id"),
                        "folder_id": data.get("folder_id") or data.get("id"),
                        "folder_name": folder_name,
                        "quiz_id": item.get("quiz_id"),
                        "title": item.get("title") or "Quiz",
                        "display_title": item.get("title") or "Quiz",
                        "question_type": item.get("question_type"),
                        "questions": item.get("questions") or [],
                    }
                    for item in quizzes
                    if isinstance(item, dict)
                ]
                generic_items = [
                    {
                        "id": item.get("id") or item.get("quiz_id"),
                        "label": item["title"],
                        "href": (
                            f"/quiz_display?quizId={item.get('quiz_id')}"
                            f"&questionType={item.get('question_type') or 'multichoice'}"
                        ),
                        "metadata": item,
                    }
                    for item in folder_items
                    if item.get("quiz_id")
                ]
                artifacts.append(
                    _resource_list_artifact(
                        resource="folder_quiz",
                        title=folder_display_title,
                        items=generic_items,
                        metadata={
                            "folder_id": data.get("folder_id") or data.get("id"),
                            "folder_name": folder_name,
                            "display_title": folder_display_title,
                        },
                    )
                )

        if result.tool_name == "folder_find_quiz_by_title":
            matches = data.get("matches")
            if isinstance(matches, list):
                match_items = [
                    {
                        "folder_id": item.get("folder_id"),
                        "folder_name": item.get("folder_name"),
                        "folder_item_id": item.get("folder_item_id"),
                        "quiz_id": item.get("quiz_id"),
                        "title": item.get("title") or "Quiz",
                        "display_title": item.get("title") or "Quiz",
                        "question_type": item.get("question_type"),
                        "questions": item.get("questions") or [],
                    }
                    for item in matches
                    if isinstance(item, dict)
                ]
                generic_items = [
                    {
                        "id": item.get("folder_item_id") or item.get("quiz_id"),
                        "label": item["title"],
                        "href": (
                            f"/quiz_display?quizId={item.get('quiz_id')}"
                            f"&questionType={item.get('question_type') or 'multichoice'}"
                        ),
                        "metadata": item,
                    }
                    for item in match_items
                    if item.get("quiz_id")
                ]
                artifacts.append(
                    _resource_list_artifact(
                        resource="folder_quiz_match",
                        title=f"Matches for {data.get('query') or 'quiz'}",
                        items=generic_items,
                    )
                )

        if result.tool_name in {"library_get_saved_quiz", "library_get_history_detail", "share_get_quiz"}:
            quiz_id = data.get("quiz_id") or data.get("id")
            question_type = data.get("question_type") or data.get("quiz_type") or "multichoice"
            artifacts.append(
                _resource_artifact(
                    resource="quiz",
                    label=str(data.get("title") or data.get("quiz_name") or "Quiz"),
                    href=(
                        f"/quiz_display?quizId={quiz_id}&questionType={question_type}"
                        if quiz_id
                        else None
                    ),
                    metadata={
                        "quiz_id": data.get("quiz_id") or data.get("id"),
                        "saved_quiz_id": data.get("id") if result.tool_name == "library_get_saved_quiz" else None,
                        "history_id": data.get("id") if result.tool_name == "library_get_history_detail" else None,
                        "title": data.get("title") or data.get("quiz_name") or "Quiz",
                        "question_type": question_type,
                    },
                )
            )

        if result.tool_name == "share_create_link":
            artifacts.append(
                AssistantArtifact(
                    type="resource",
                    data={
                        "resource": "share_link",
                        "label": "Shared quiz",
                        "href": data.get("link"),
                        "metadata": data,
                        "actions": [
                            {
                                "type": "copy_to_clipboard",
                                "label": "Copy link",
                                "value": data.get("link"),
                            }
                        ]
                        if data.get("link")
                        else [],
                    },
                )
            )

        if result.tool_name == "share_send_email":
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="share_email",
                    label=outcome_artifact_label(outcome) or "Share email sent",
                    metadata=data,
                )
            )

        if result.tool_name == "folder_add_saved_quiz":
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="folder_item",
                    label=outcome_artifact_label(outcome) or "Quiz added to folder.",
                    metadata=data,
                )
            )

        if result.tool_name == "folder_move_quiz":
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="folder_item",
                    label=outcome_artifact_label(outcome) or "Quiz moved.",
                    metadata=data,
                )
            )

        if result.tool_name == "folder_delete":
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="folder",
                    label=outcome_artifact_label(outcome) or "Folder deleted.",
                    metadata=data,
                )
            )

        if result.tool_name == "folder_remove_quiz":
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="folder_item",
                    label=outcome_artifact_label(outcome) or "Quiz removed from folder.",
                    metadata=data,
                )
            )

        if result.tool_name == "folder_rename":
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="folder",
                    label=outcome_artifact_label(outcome) or "Folder renamed.",
                    metadata=data,
                )
            )

        if result.tool_name == "quiz_export_link":
            artifacts.append(
                AssistantArtifact(
                    type="file_action",
                    data={
                        "resource": "quiz_export",
                        "action_id": data.get("action_id"),
                        "label": data.get("label") or "Download quiz",
                        "href": data.get("href"),
                        "method": "GET",
                        "auto_execute": bool(data.get("auto_execute")),
                        "max_retries": data.get("max_retries") or 3,
                        "metadata": data,
                    },
                )
            )

        if result.tool_name in {"live_quiz_get_access_link", "live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
            if data.get("found") is False:
                artifacts.append(
                    _status_artifact(
                        resource="live_quiz_link",
                        label=data.get("message") or "No active live quiz link exists.",
                        metadata=data,
                    )
                )
            else:
                link = data.get("live_quiz_link")
                artifacts.append(
                    _resource_artifact(
                        resource="live_quiz_link",
                        label=str(data.get("title") or "Live quiz link"),
                        href=link,
                        metadata=data,
                        actions=[
                            {
                                "type": "copy_to_clipboard",
                                "label": "Copy link",
                                "value": link,
                            }
                        ]
                        if link
                        else [],
                    )
                )

        if result.tool_name == "live_quiz_send_invites":
            if final_result is result and result.tool_name in suppress_final_status_tools:
                continue
            outcome = outcomes[result.step_id]
            artifacts.append(
                _status_artifact(
                    resource="live_quiz_invite",
                    label=outcome_artifact_label(outcome) or "Live quiz invites sent.",
                    metadata=data,
                )
            )

        if result.tool_name == "notification_list":
            notifications = _items_from_result(data.get("items") if isinstance(data, dict) else data)
            items = [
                {
                    "id": item.get("id"),
                    "label": item.get("title") or "Notification",
                    "href": item.get("action_url") or "/notifications",
                    "metadata": item,
                }
                for item in notifications
                if isinstance(item, dict)
            ]
            artifacts.append(
                _resource_list_artifact(
                    resource="notification",
                    title="Notifications",
                    items=items,
                )
            )

    return artifacts
