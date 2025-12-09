from flask import Blueprint

bp = Blueprint("vendors", __name__, url_prefix="/vendors")

from . import routes  # noqa
