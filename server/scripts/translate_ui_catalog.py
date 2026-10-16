"""Generate public UI translation patches; never writes files or prints credentials.

Run from the repository root. Output is JSON for review, not automatically published.
"""
import argparse
import asyncio
import json
import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--namespace", default="ui")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--count", type=int, default=32)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / "server/.env")
    if args.diagnose:
        print(json.dumps({"provider": os.getenv("TRANSLATION_PROVIDER", "none"),
                          "model": os.getenv("TRANSLATION_MODEL", "default"),
                          "custom_url_configured": bool(os.getenv("TRANSLATION_PROVIDER_URL")),
                          "gemini_key_present": bool(os.getenv("GEMINI_API_KEY"))}))
        return
    if args.model:
        os.environ["TRANSLATION_MODEL"] = args.model
    os.environ["TRANSLATION_PROVIDER_TIMEOUT_SECONDS"] = "120"
    if args.list_models:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get("https://generativelanguage.googleapis.com/v1beta/models",
                    headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")})
                response.raise_for_status()
                print(json.dumps([item["name"] for item in response.json().get("models", [])
                    if "generateContent" in item.get("supportedGenerationMethods", [])]))
        except Exception as exc:
            print(json.dumps({"error": type(exc).__name__, "http_status": getattr(getattr(exc, "response", None), "status_code", None)}))
        return
    if not args.locale:
        parser.error("--locale is required for translation")
    # This script serves no HTTP/MCP requests; give required app config a process-only value.
    os.environ.setdefault("ASSISTANT_INTERNAL_MCP_SECRET", secrets.token_urlsafe(32))
    from server.app.i18n.provider import translate_messages
    from server.app.i18n.catalogs import validate_messages
    prefix = "" if args.namespace == "translation" else args.namespace + "."
    source = json.loads((root / f"client/src/features/locale/messages/{prefix}en.json").read_text())
    messages = dict(list(source.items())[args.offset:args.offset + args.count])
    try:
        result = validate_messages(messages, await translate_messages(messages, locale=args.locale))
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        # Exception reprs/HTTP bodies can include keys or configuration values.
        status = getattr(getattr(exc.__cause__, "response", None), "status_code", None)
        print(json.dumps({"error": type(exc).__name__, "http_status": status,
                          "cause": type(exc.__cause__).__name__ if exc.__cause__ else None}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
