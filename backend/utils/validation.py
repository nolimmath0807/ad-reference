import re


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"\d", password):
        return False
    return True


def sanitize_string(s: str) -> str:
    return s.strip()
