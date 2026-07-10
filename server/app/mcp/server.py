from mcp.server.fastmcp import FastMCP

from server.app.mcp.resources.category_resources import (
    categories_resource,
    category_resource,
    category_subcategory_resource,
)
from server.app.mcp.resources.library_resources import (
    folder_resource,
    folders_resource,
    quiz_history_detail_resource,
    quiz_history_resource,
    saved_quizzes_resource,
)
from server.app.mcp.resources.quiz_resources import quiz_resource, shared_quiz_resource
from server.app.mcp.telemetry import instrument_mcp_call
from server.app.mcp.tools.answer_tools import quiz_get_answers
from server.app.mcp.tools.category_tools import (
    category_browse_questions,
    category_list,
    category_list_quiz_types,
    category_list_subcategories,
)
from server.app.mcp.tools.folder_tools import (
    folder_add_saved_quiz,
    folder_create,
    folder_delete,
    folder_find_quiz_by_title,
    folder_get,
    folder_get_by_name,
    folder_list,
    folder_move_quiz,
    folder_remove_quiz,
    folder_rename,
)
from server.app.mcp.tools.library_tools import (
    library_find_saved_quiz_by_title,
    library_get_history_detail,
    library_get_saved_quiz,
    library_list_history,
    library_list_saved_quizzes,
    library_save_quiz,
    saved_quiz_delete,
    saved_quiz_rename,
)
from server.app.mcp.tools.live_quiz_tools import (
    live_quiz_ensure_access_link,
    live_quiz_create_access_link,
    live_quiz_get_access_link,
    live_quiz_send_invites,
)
from server.app.mcp.tools.export_tools import quiz_export_link
from server.app.mcp.tools.notification_tools import (
    notification_delete,
    notification_list,
    notification_mark_read,
)
from server.app.mcp.tools.quiz_tools import quiz_generate
from server.app.mcp.tools.share_tools import share_create_link, share_get_quiz, share_send_email


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        name="QuizApp MCP Server",
        instructions=(
            "QuizApp MCP exposes quiz generation, public category browsing, shared quiz reads, "
            "live quiz link operations, and authenticated user-library operations."
        ),
        stateless_http=True,
        json_response=True,
    )

    mcp.tool(
        name="category_list",
        description="List public QuizApp categories.",
    )(instrument_mcp_call("category_list")(category_list))
    mcp.tool(
        name="category_list_subcategories",
        description="List public subcategories for a category.",
    )(instrument_mcp_call("category_list_subcategories")(category_list_subcategories))
    mcp.tool(
        name="category_list_quiz_types",
        description="List quiz types available for a category/subcategory.",
    )(instrument_mcp_call("category_list_quiz_types")(category_list_quiz_types))
    mcp.tool(
        name="category_browse_questions",
        description="Browse public category questions from the canonical V2 quiz store.",
    )(instrument_mcp_call("category_browse_questions")(category_browse_questions))

    mcp.tool(
        name="quiz_generate",
        description="Generate a quiz through the existing QuizApp generation pipeline.",
    )(instrument_mcp_call("quiz_generate")(quiz_generate))
    mcp.tool(
        name="quiz_get_answers",
        description="Return an authenticated user's answer key for an owned or library quiz.",
    )(instrument_mcp_call("quiz_get_answers")(quiz_get_answers))

    mcp.tool(
        name="share_get_quiz",
        description="Read a public/shared quiz by quiz ID.",
    )(instrument_mcp_call("share_get_quiz")(share_get_quiz))
    mcp.tool(
        name="share_create_link",
        description="Create a QuizApp share URL for a quiz ID.",
    )(instrument_mcp_call("share_create_link")(share_create_link))
    mcp.tool(
        name="share_send_email",
        description="Send an existing QuizApp share URL to an email recipient.",
    )(instrument_mcp_call("share_send_email")(share_send_email))
    mcp.tool(
        name="quiz_export_link",
        description="Prepare an authenticated quiz export/download action.",
    )(instrument_mcp_call("quiz_export_link")(quiz_export_link))

    mcp.tool(
        name="live_quiz_get_access_link",
        description="Return an active non-expired live quiz access link for an owned quiz.",
    )(instrument_mcp_call("live_quiz_get_access_link")(live_quiz_get_access_link))
    mcp.tool(
        name="live_quiz_create_access_link",
        description="Create or reuse an active live quiz access link for an owned quiz.",
    )(instrument_mcp_call("live_quiz_create_access_link")(live_quiz_create_access_link))
    mcp.tool(
        name="live_quiz_ensure_access_link",
        description="Return an active live quiz access link, or create one when duration is supplied.",
    )(instrument_mcp_call("live_quiz_ensure_access_link")(live_quiz_ensure_access_link))
    mcp.tool(
        name="live_quiz_send_invites",
        description="Send a live quiz access link to one or more invitee emails.",
    )(instrument_mcp_call("live_quiz_send_invites")(live_quiz_send_invites))

    mcp.tool(
        name="library_list_saved_quizzes",
        description="List authenticated user's saved quizzes.",
    )(instrument_mcp_call("library_list_saved_quizzes")(library_list_saved_quizzes))
    mcp.tool(
        name="library_get_saved_quiz",
        description="Get an authenticated user's saved quiz.",
    )(instrument_mcp_call("library_get_saved_quiz")(library_get_saved_quiz))
    mcp.tool(
        name="library_find_saved_quiz_by_title",
        description="Find authenticated user's saved quizzes by title for lookup workflows.",
    )(instrument_mcp_call("library_find_saved_quiz_by_title")(library_find_saved_quiz_by_title))
    mcp.tool(
        name="library_save_quiz",
        description="Save a quiz into the authenticated user's library.",
    )(instrument_mcp_call("library_save_quiz")(library_save_quiz))
    mcp.tool(
        name="saved_quiz_rename",
        description="Rename an authenticated user's saved quiz display title.",
    )(instrument_mcp_call("saved_quiz_rename")(saved_quiz_rename))
    mcp.tool(
        name="saved_quiz_delete",
        description="Delete an authenticated user's saved quiz reference.",
    )(instrument_mcp_call("saved_quiz_delete")(saved_quiz_delete))
    mcp.tool(
        name="library_list_history",
        description="List authenticated user's quiz history.",
    )(instrument_mcp_call("library_list_history")(library_list_history))
    mcp.tool(
        name="library_get_history_detail",
        description="Get a quiz-history detail for the authenticated user.",
    )(instrument_mcp_call("library_get_history_detail")(library_get_history_detail))

    mcp.tool(
        name="folder_list",
        description="List authenticated user's folders.",
    )(instrument_mcp_call("folder_list")(folder_list))
    mcp.tool(
        name="folder_get",
        description="Get an authenticated user's folder.",
    )(instrument_mcp_call("folder_get")(folder_get))
    mcp.tool(
        name="folder_get_by_name",
        description="Get an authenticated user's folder and contained quizzes by folder name.",
    )(instrument_mcp_call("folder_get_by_name")(folder_get_by_name))
    mcp.tool(
        name="folder_find_quiz_by_title",
        description="Find whether a quiz title exists in any authenticated user folder.",
    )(instrument_mcp_call("folder_find_quiz_by_title")(folder_find_quiz_by_title))
    mcp.tool(
        name="folder_create",
        description="Create a folder for the authenticated user.",
    )(instrument_mcp_call("folder_create")(folder_create))
    mcp.tool(
        name="folder_add_saved_quiz",
        description="Add a saved quiz to one of the authenticated user's folders.",
    )(instrument_mcp_call("folder_add_saved_quiz")(folder_add_saved_quiz))
    mcp.tool(
        name="folder_rename",
        description="Rename one of the authenticated user's folders.",
    )(instrument_mcp_call("folder_rename")(folder_rename))
    mcp.tool(
        name="folder_delete",
        description="Delete one of the authenticated user's folders.",
    )(instrument_mcp_call("folder_delete")(folder_delete))
    mcp.tool(
        name="folder_remove_quiz",
        description="Remove a quiz item from one of the authenticated user's folders.",
    )(instrument_mcp_call("folder_remove_quiz")(folder_remove_quiz))
    mcp.tool(
        name="folder_move_quiz",
        description="Move a quiz item between two authenticated user folders.",
    )(instrument_mcp_call("folder_move_quiz")(folder_move_quiz))

    mcp.tool(
        name="notification_list",
        description="List authenticated user's notifications.",
    )(instrument_mcp_call("notification_list")(notification_list))
    mcp.tool(
        name="notification_mark_read",
        description="Mark an authenticated user's notification as read.",
    )(instrument_mcp_call("notification_mark_read")(notification_mark_read))
    mcp.tool(
        name="notification_delete",
        description="Delete an authenticated user's notification.",
    )(instrument_mcp_call("notification_delete")(notification_delete))

    mcp.resource("categories://list")(instrument_mcp_call("resource.categories")(categories_resource))
    mcp.resource("category://{category_slug}")(instrument_mcp_call("resource.category")(category_resource))
    mcp.resource("category://{category_slug}/{subcategory_slug}")(
        instrument_mcp_call("resource.category_subcategory")(category_subcategory_resource)
    )
    mcp.resource("quiz://{quiz_id}")(instrument_mcp_call("resource.quiz")(quiz_resource))
    mcp.resource("shared-quiz://{quiz_id}")(instrument_mcp_call("resource.shared_quiz")(shared_quiz_resource))
    mcp.resource("saved-quizzes://me")(instrument_mcp_call("resource.saved_quizzes")(saved_quizzes_resource))
    mcp.resource("quiz-history://me")(instrument_mcp_call("resource.quiz_history")(quiz_history_resource))
    mcp.resource("quiz-history://{history_id}")(
        instrument_mcp_call("resource.quiz_history_detail")(quiz_history_detail_resource)
    )
    mcp.resource("folders://me")(instrument_mcp_call("resource.folders")(folders_resource))
    mcp.resource("folder://{folder_id}")(instrument_mcp_call("resource.folder")(folder_resource))

    return mcp
