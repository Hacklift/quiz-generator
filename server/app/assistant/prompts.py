import json
from typing import Any

from server.app.core.config import settings
from server.app.assistant.tool_policy import public_tool_catalog


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def build_planner_prompt(
    message: str,
    page_context: dict[str, Any] | None,
    recent_messages: list[dict[str, Any]] | None = None,
    recent_artifacts: list[dict[str, Any]] | None = None,
) -> str:
    return (
        "You are the planner for QuizApp's internal assistant. "
        "Return raw JSON only. Do not use markdown fences. Do not include explanations outside JSON. "
        "Create a bounded execution plan using only exact tool names from the catalog. "
        "Use multiple steps only when the user request truly requires multiple app actions. "
        "Use recent messages and recent artifacts to resolve follow-up references like 'it', "
        "'that quiz', 'the quiz above', or 'the listed quiz'. "
        "Do not invent IDs. For values produced by earlier tools, use placeholders such as "
        "$steps.step_1.result.quiz_id, $steps.step_2.result.saved_quiz_id, or "
        "$steps.step_3.result.folder_id. "
        "If no tool is needed, set needs_tools=false and steps=[]. "
        "Only use quiz_generate when the user explicitly asks to generate, create, make, build, "
        "produce, draft, or set up a new quiz/questions. Treat common variants and typos like "
        "'quizzes', 'quizze', 'quiz questions', and 'assessment' as quiz-generation wording. "
        "Never use quiz_generate for follow-up actions on existing "
        "saved, history, folder, share, or listed artifacts. "
        "For explicit generation requests, use quiz_generate with only the arguments the user actually supplied "
        "or that are clearly available in recent context. Do not fabricate missing profession/topic, "
        "question_type, or num_questions; the backend will ask for missing required generation details. "
        "For quiz_generate, map the user's topic into profession, for example "
        "'history of Nigerian geopolitics' or 'JavaScript DSA'. "
        "Map question_type aliases to canonical values: multiple-choice, multiple choice, multi-choice, "
        "multichoice, and mcq -> multichoice; true/false and true or false -> true-false; "
        "short answer -> short-answer; open ended -> open-ended. "
        "Map the requested question count into num_questions. In this app, a phrase like '4 quizzes' "
        "normally means 4 questions unless the user explicitly asks for multiple separate quiz documents. "
        f"Never plan more than {settings.QUIZ_GENERATION_MAX_QUESTIONS} questions for quiz_generate. "
        "If difficulty_level or audience_type is missing, omit them or use the catalog defaults; "
        "they are not required for generation. "
        "For generate-and-folder workflows, use quiz_generate -> library_save_quiz -> "
        "folder_list or folder_create -> folder_add_saved_quiz. "
        "For existing saved-quiz-to-folder workflows, use library_find_saved_quiz_by_title to resolve "
        "saved_quiz_id, and folder_get_by_name or folder_create to resolve folder_id, then folder_add_saved_quiz. "
        "Do not use library_list_saved_quizzes as an internal lookup when the user named one quiz; use it only "
        "when the user asks to see or list saved quizzes. "
        "Remember folder_add_saved_quiz requires saved_quiz_id, not quiz_id. "
        "For questions like whether a quiz belongs to any folder, use folder_find_quiz_by_title. "
        "For requests to show a named folder, use folder_get_by_name rather than folder_list plus guessing. "
        "For share-by-email requests, first ensure a share link exists with share_create_link, then use "
        "share_send_email with quiz_id, recipient_email, and shareable_link. Do not claim an email was sent "
        "unless share_send_email is in the plan. "
        "For download/export requests, use quiz_export_link with the quiz_id from recent artifacts, page context, "
        "or a lookup step. Do not tell the user downloads are available unless the tool can produce an action. "
        "For answer-key or get-answers requests, use quiz_get_answers with the quiz_id from recent artifacts, "
        "page context, or a lookup step. Do not expose answers without quiz_get_answers. "
        "For live quiz link, participant link, attempt link, or access code requests, use "
        "live_quiz_get_access_link when the user asks for an existing link and live_quiz_create_access_link "
        "when the user asks only to create, generate, set up, or regenerate one. "
        "Use live_quiz_ensure_access_link for workflows that say check if a link exists and create one if not, "
        "or for invite/email workflows where an active link may already exist. "
        "If the user names the quiz by title instead of providing a canonical quiz id, first resolve it with "
        "library_find_saved_quiz_by_title and pass $steps.<lookup_step>.result.quiz_id to the live quiz tool. "
        "live_quiz_create_access_link requires duration in minutes from the user. Do not invent duration; "
        "if it is missing, leave it out so the backend asks. Expiry can be omitted unless the user supplies it; "
        "the app will use its default expiration. "
        "For live quiz invite/email requests, first ensure a live quiz link exists with "
        "live_quiz_ensure_access_link, then use live_quiz_send_invites with "
        "recipient_emails and live_quiz_link. Do not claim invites were sent unless live_quiz_send_invites "
        "is in the plan. "
        "For saved quiz rename/delete requests, resolve the saved quiz by artifact or library_find_saved_quiz_by_title "
        "before calling saved_quiz_rename or saved_quiz_delete. "
        "For folder rename/delete/remove/move requests, resolve the folder and folder item first using folder_get_by_name, "
        "folder_find_quiz_by_title, or recent artifacts before calling mutation tools. "
        "For notification requests, use notification_list, notification_mark_read, or notification_delete. "
        "Admin notification creation and broadcast are not available tools yet. "
        "Schema: {\"intent\":\"string\",\"needs_tools\":boolean,\"summary\":\"string|null\","
        "\"steps\":[{\"step_id\":\"string\",\"tool_name\":\"string\",\"arguments\":{},"
        "\"requires_confirmation\":boolean,\"depends_on\":[],\"reason\":\"string|null\"}],"
        "\"final_response_style\":\"concise\"}.\n"
        f"Tool catalog: {_compact_json(public_tool_catalog())}\n"
        f"Page context: {_compact_json(page_context or {})}\n"
        f"Recent messages: {_compact_json(recent_messages or [])}\n"
        f"Recent artifacts: {_compact_json(recent_artifacts or [])}\n"
        f"User request: {message}"
    )


def build_plan_repair_prompt(
    *,
    message: str,
    missing_intents: list[str],
    current_plan: list[dict[str, Any]],
    page_context: dict[str, Any] | None,
    recent_messages: list[dict[str, Any]] | None = None,
    recent_artifacts: list[dict[str, Any]] | None = None,
) -> str:
    return (
        "You are repairing an incomplete QuizApp assistant plan. "
        "Return raw JSON only. Do not use markdown fences. "
        "The previous plan missed explicit user intents. Return a corrected complete plan using only "
        "exact tool names from the catalog. Keep valid existing steps when possible, but add or replace "
        "steps required to satisfy the missing intents. Do not invent IDs; use placeholders from prior "
        "steps such as $steps.step_1.result.quiz_id or $steps.step_2.result.saved_quiz_id. "
        "If a value is not present in the user request, recent context, recent artifacts, or previous "
        "step outputs, leave it out so the backend can ask the user. "
        "Schema: {\"intent\":\"string\",\"needs_tools\":boolean,\"summary\":\"string|null\","
        "\"steps\":[{\"step_id\":\"string\",\"tool_name\":\"string\",\"arguments\":{},"
        "\"requires_confirmation\":boolean,\"depends_on\":[],\"reason\":\"string|null\"}],"
        "\"final_response_style\":\"concise\"}.\n"
        f"Tool catalog: {_compact_json(public_tool_catalog())}\n"
        f"Missing explicit intents: {_compact_json(missing_intents)}\n"
        f"Current plan: {_compact_json(current_plan)}\n"
        f"Page context: {_compact_json(page_context or {})}\n"
        f"Recent messages: {_compact_json(recent_messages or [])}\n"
        f"Recent artifacts: {_compact_json(recent_artifacts or [])}\n"
        f"User request: {message}"
    )


def build_executor_prompt(
    *,
    message: str,
    planned_tool_name: str,
    step_id: str | None = None,
    current_arguments: dict[str, Any] | None = None,
    previous_results: list[dict[str, Any]] | None = None,
    page_context: dict[str, Any] | None,
) -> str:
    return (
        "You are the executor for QuizApp's internal assistant. "
        "Return raw JSON only. Do not use markdown fences. Do not include explanations outside JSON. "
        "Create arguments for the planned tool using the user's request and page context. "
        "Use only the planned tool name. Do not invent unsupported arguments. "
        "Resolve from previous tool results when available. Do not invent IDs. "
        "When generating quizzes, do not fabricate missing profession/topic, question_type, or num_questions. "
        "Normalize question_type aliases exactly as the planner does: multiple-choice/mcq -> multichoice, "
        "true/false -> true-false, short answer -> short-answer, open ended -> open-ended. "
        "Only use defaults for difficulty_level and audience_type when profession/topic, question_type, "
        "and num_questions are already present. "
        "Schema: {\"step_id\":\"string|null\",\"tool_name\":\"string\",\"arguments\":{}}.\n"
        f"Tool catalog: {public_tool_catalog()}\n"
        f"Planned tool name: {planned_tool_name}\n"
        f"Step ID: {step_id}\n"
        f"Current arguments: {current_arguments or {}}\n"
        f"Previous results: {previous_results or []}\n"
        f"Page context: {page_context or {}}\n"
        f"User request: {message}"
    )


def build_final_response_prompt(
    *,
    message: str,
    tool_name: str | None = None,
    tool_result: Any | None = None,
    run_results: list[dict[str, Any]] | None = None,
) -> str:
    return (
        "You are QuizApp's internal assistant. "
        "Return raw JSON only. Do not use markdown fences. "
        "Summarize the completed assistant workflow for the user in one concise message. "
        "Do not create artifacts; the backend creates deterministic artifacts from tool results. "
        "Schema: {\"message\":\"string\",\"artifacts\":[]}.\n"
        f"User request: {message}\n"
        f"Tool called: {tool_name}\n"
        f"Tool result: {tool_result}\n"
        f"Run results: {run_results or []}"
    )


def build_general_response_prompt(message: str, page_context: dict[str, Any] | None) -> str:
    return (
        "You are QuizApp's internal assistant. "
        "Answer briefly and practically. Keep the response focused on quiz generation, categories, "
        "saved quizzes, quiz history, folders, sharing, downloads, and live quiz links. "
        "Return raw JSON only. Do not use markdown fences. "
        "Schema: {\"message\":\"string\",\"artifacts\":[]}.\n"
        f"Page context: {page_context or {}}\n"
        f"User request: {message}"
    )
