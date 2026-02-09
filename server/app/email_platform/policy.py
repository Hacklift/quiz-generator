def chain_for(purpose: str, priority: str = "default") -> list[str]:


    if purpose in ("verification", "password_reset"):

        return ["celery", "background", "direct"]


    return ["celery", "background"]

