def chain_for(purpose: str, priority: str = "default") -> list[str]:
    # Hardcoded for now; move to YAML later
    if purpose in ("verification", "password_reset"):
        return ["celery", "background", "direct"]
    # default for quiz links
    return ["celery", "background"]
