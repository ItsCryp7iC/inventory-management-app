from flask import Blueprint

bp = Blueprint("assets", __name__, url_prefix="/assets")

from . import routes  # noqa
