from server.app.mcp.tools.category_tools import (
    category_list,
    category_list_quiz_types,
    category_list_subcategories,
)


async def categories_resource() -> dict:
    return {"categories": await category_list()}


async def category_resource(category_slug: str) -> dict:
    return {
        "category": category_slug,
        "subcategories": await category_list_subcategories(category_slug),
    }


async def category_subcategory_resource(category_slug: str, subcategory_slug: str) -> dict:
    return {
        "category": category_slug,
        "subcategory": subcategory_slug,
        "quiz_types": await category_list_quiz_types(category_slug, subcategory_slug),
    }
