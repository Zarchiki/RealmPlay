"""Exception contracts shared by LLM transport and chat orchestration."""


class GenerationCancelled(Exception):
    """Raised when an in-flight local generation is cancelled by the user."""
