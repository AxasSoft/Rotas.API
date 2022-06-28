from typing import Optional


def try_parse_int(s: Optional[str]):
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        return None
