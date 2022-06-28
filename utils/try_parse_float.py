from typing import Optional


def try_parse_float(s: Optional[str]):
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None
