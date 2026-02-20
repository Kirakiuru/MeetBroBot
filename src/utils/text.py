from html import escape as _html_escape


def safe(text: str | None) -> str:
    """Escape HTML special chars in user-provided text."""
    if text is None:
        return ""
    return _html_escape(str(text), quote=False)
