"""Safe provider errors: never expose upstream bodies, prompts or credentials."""
from fastapi import HTTPException


class GenerationProviderError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


MESSAGES = {
    "notConfigured": "{provider} is not configured. Ask the administrator to configure its API key or select another provider.",
    "credentials": "{provider} rejected its API credentials. Check the provider key or select another provider.",
    "billing": "{provider} requires payment or credits. Check provider billing or select another provider.",
    "quota": "{provider} has reached a quota or rate limit. Try again later or select another provider.",
    "model": "The configured {provider} model is unavailable. Ask the administrator to check the model setting.",
    "invalidOutput": "{provider} did not return a complete quiz in the requested format and language. Retry or select another provider.",
    "blocked": "{provider} could not complete this request. Adjust the topic or document and try again.",
    "timeout": "{provider} took too long to respond. Retry or select another provider.",
    "unavailable": "{provider} is temporarily unavailable. Retry or select another provider.",
}


def generation_http_error(exc: Exception, provider: str, *, status_code: int = 503) -> HTTPException:
    upstream_status = getattr(getattr(exc, "response", None), "status_code", None)
    code = exc.code if isinstance(exc, GenerationProviderError) else {
        401: "credentials", 403: "credentials", 402: "billing", 429: "quota", 404: "model",
    }.get(upstream_status, "invalidOutput" if isinstance(exc, (ValueError, TypeError, KeyError, IndexError)) else "unavailable")
    name = "Gemini" if provider == "gemini" else "Hugging Face"
    return HTTPException(status_code=status_code, detail={
        "code": code, "provider": name, "message": MESSAGES[code].format(provider=name),
    })
