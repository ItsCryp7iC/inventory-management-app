from flask import render_template
from . import bp
from app.models import Asset


@bp.route("/")
def list_assets():
    assets = Asset.query.order_by(Asset.id.desc()).all()
    return render_template("assets/list.html", assets=assets)
