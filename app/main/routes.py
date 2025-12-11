from flask_login import login_required

from datetime import date, timedelta
from flask import render_template
from . import bp
from app.models import Asset


@bp.route("/")
@login_required
def index():
    # Basic stats
    total_assets = Asset.query.count()
    in_use_count = Asset.query.filter_by(status="in_use").count()
    in_stock_count = Asset.query.filter_by(status="in_stock").count()
    retired_count = Asset.query.filter_by(status="retired").count()

    # Assets needing attention
    today = date.today()
    warning_threshold = today + timedelta(days=30)

    attention_query = Asset.query

    attention_assets = attention_query.filter(
        (
            # Warranty expired or expiring soon
            (Asset.warranty_expiry_date != None)  # noqa: E711
            & (Asset.warranty_expiry_date <= warning_threshold)
            & (Asset.status.notin_(["retired", "disposed"]))
        )
        |
        # OR status under_repair
        (Asset.status == "under_repair")
        |
        # OR missing key metadata
        (Asset.location_id == None)  # noqa: E711
        |
        (Asset.category_id == None)  # noqa: E711
    ).order_by(Asset.warranty_expiry_date.asc().nullslast(), Asset.id.desc()).limit(10).all()

    return render_template(
        "index.html",
        total_assets=total_assets,
        in_use_count=in_use_count,
        in_stock_count=in_stock_count,
        retired_count=retired_count,
        attention_assets=attention_assets,
    )
