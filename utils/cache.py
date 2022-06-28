from functools import wraps

from flask import make_response


def nocache(f):
    """
    disable cache decorator
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        r = make_response(f(*args, **kwargs))

        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        r.headers['Cache-Control'] = 'public, max-age=0'
        return r

    return decorated_function
