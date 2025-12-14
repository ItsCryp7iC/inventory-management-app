from flask_login import login_required

from datetime import date, timedelta
from flask import render_template
from sqlalchemy import func

from . import bp
from app.extensions import db
from app.models import Asset, Category, Location, AssetEvent


@bp.route("/")
@login_required
def index():
    # Basic stats
    total_assets = Asset.query.count()
    assigned_count = Asset.query.filter(Asset.status.in_(["assigned", "in_use"])).count()
    in_stock_count = Asset.query.filter_by(status="in_stock").count()
    repair_count = Asset.query.filter_by(status="repair").count()
    damaged_count = Asset.query.filter_by(status="damaged").count()
    missing_count = Asset.query.filter_by(status="missing").count()

    # Assets needing attention
    today = date.today()
    warning_threshold = today + timedelta(days=30)

    attention_assets = (
        Asset.query
        .filter(Asset.status.in_(["repair", "damaged", "missing"]))
        .order_by(Asset.updated_at.desc(), Asset.id.desc())
        .all()
    )

    # Aggregates for charts
    category_breakdown = [
        {"name": name, "count": cnt}
        for name, cnt in db.session.query(Category.name, func.count(Asset.id))
        .join(Asset, Asset.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
        .all()
    ]

    location_breakdown = [
        {"name": name, "count": cnt}
        for name, cnt in db.session.query(Location.name, func.count(Asset.id))
        .join(Asset, Asset.location_id == Location.id)
        .group_by(Location.id, Location.name)
        .order_by(Location.name)
        .all()
    ]

    monthly_events = [
        {"month": month, "count": cnt}
        for month, cnt in db.session.query(
            func.strftime("%Y-%m", AssetEvent.created_at).label("month"),
            func.count(AssetEvent.id),
        )
        .group_by("month")
        .order_by("month")
        .all()
    ]

    return render_template(
        "index.html",
        total_assets=total_assets,
        assigned_count=assigned_count,
        in_stock_count=in_stock_count,
        repair_count=repair_count,
        damaged_count=damaged_count,
        missing_count=missing_count,
        attention_assets=attention_assets,
        category_breakdown=category_breakdown,
        location_breakdown=location_breakdown,
        monthly_events=monthly_events,
    )
