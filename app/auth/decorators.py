from functools import wraps
from flask import abort
from flask_login import login_required, current_user


def admin_required(view_func):
    """
    Requires:
      - user is logged in
      - user.is_admin is True
    Returns 403 for non-admin.
    """
    @wraps(view_func)
    @login_required
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper
