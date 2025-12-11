from .extensions import db
from datetime import datetime



class TimestampMixin:
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False
    )


class Location(TimestampMixin, db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(50), nullable=True, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    assets = db.relationship("Asset", back_populates="location")

    def __repr__(self):
        return f"<Location {self.name}>"


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    subcategories = db.relationship("SubCategory", back_populates="category")
    assets = db.relationship("Asset", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class SubCategory(TimestampMixin, db.Model):
    __tablename__ = "subcategories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False
    )
    category = db.relationship("Category", back_populates="subcategories")

    assets = db.relationship("Asset", back_populates="subcategory")

    __table_args__ = (
        db.UniqueConstraint("name", "category_id", name="uq_subcategory_name_category"),
    )

    def __repr__(self):
        return f"<SubCategory {self.name} ({self.category.name if self.category else '-'})>"


class Vendor(TimestampMixin, db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    contact_email = db.Column(db.String(150), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    address = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    assets = db.relationship("Asset", back_populates="vendor")

    def __repr__(self):
        return f"<Vendor {self.name}>"


class Asset(TimestampMixin, db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)

    asset_tag = db.Column(db.String(100), nullable=True, unique=True)  # internal tag
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)

    serial_number = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="in_use")
    # status examples: in_use, in_stock, under_repair, retired, disposed

    purchase_date = db.Column(db.Date, nullable=True)
    warranty_expiry_date = db.Column(db.Date, nullable=True)
    cost = db.Column(db.Numeric(12, 2), nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    subcategory_id = db.Column(db.Integer, db.ForeignKey("subcategories.id"), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=True)

    category = db.relationship("Category", back_populates="assets")
    subcategory = db.relationship("SubCategory", back_populates="assets")
    location = db.relationship("Location", back_populates="assets")
    vendor = db.relationship("Vendor", back_populates="assets")

    notes = db.Column(db.Text, nullable=True)

        # assignment fields
    assigned_to = db.Column(db.String(150), nullable=True)          # Person name
    assigned_department = db.Column(db.String(150), nullable=True)  # Department/team
    assigned_email = db.Column(db.String(150), nullable=True)       # Email (if relevant)
    assigned_at = db.Column(db.Date, nullable=True)                 # Date of assignment

    events = db.relationship(
        "AssetEvent",
        backref="asset",
        lazy="dynamic",
        order_by="AssetEvent.created_at.desc()",
        cascade="all, delete-orphan",
    )  
    
    def __repr__(self):
        return f"<Asset {self.name} ({self.status})>"


class AssetEvent(db.Model):
    __tablename__ = "asset_events"

    id = db.Column(db.Integer, primary_key=True)

    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)

    event_type = db.Column(db.String(50), nullable=False)  
    note = db.Column(db.Text, nullable=True)

    from_status = db.Column(db.String(50), nullable=True)
    to_status = db.Column(db.String(50), nullable=True)

    from_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    from_location = db.relationship(
        "Location",
        foreign_keys=[from_location_id],
        lazy="joined"
    )

    to_location = db.relationship(
        "Location",
        foreign_keys=[to_location_id],
        lazy="joined"
    )


    def __repr__(self):
        return f"<AssetEvent {self.event_type} for Asset {self.asset_id} at {self.created_at}>"
