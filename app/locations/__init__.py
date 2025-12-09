from flask import Blueprint

bp = Blueprint("locations", __name__, url_prefix="/locations")

from . import routes  # noqa
