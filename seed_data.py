from app import create_app
from app.extensions import db
from app.models import Location, Category, SubCategory, Vendor


def get_or_create(model, defaults=None, **kwargs):
    """Simple helper to avoid duplicate seed rows."""
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    return instance, True


def seed():
    app = create_app()
    with app.app_context():
        print("Seeding initial data...")

        # Locations
        mirpur, _ = get_or_create(
            Location,
            name="Mirpur DOHS Office",
            code="MD-OFFICE",
        )
        dhaka_wh, _ = get_or_create(
            Location,
            name="Dhaka Warehouse",
            code="DHK-WH",
        )
        remote, _ = get_or_create(
            Location,
            name="Remote / WFH",
            code="REMOTE",
        )

        # Categories & Subcategories
        laptop_cat, _ = get_or_create(
            Category,
            name="Laptop",
            code="LAPTOP",
        )
        desktop_cat, _ = get_or_create(
            Category,
            name="Desktop",
            code="DESKTOP",
        )
        network_cat, _ = get_or_create(
            Category,
            name="Networking",
            code="NETWORK",
        )

        get_or_create(SubCategory, name="Ultrabook", category=laptop_cat)
        get_or_create(SubCategory, name="Business Laptop", category=laptop_cat)
        get_or_create(SubCategory, name="All-in-One", category=desktop_cat)
        get_or_create(SubCategory, name="Tower", category=desktop_cat)
        get_or_create(SubCategory, name="Switch", category=network_cat)
        get_or_create(SubCategory, name="Router", category=network_cat)
        get_or_create(SubCategory, name="Access Point", category=network_cat)

        # Vendors
        get_or_create(Vendor, name="Dell")
        get_or_create(Vendor, name="HP")
        get_or_create(Vendor, name="Lenovo")
        get_or_create(Vendor, name="Cisco")
        get_or_create(Vendor, name="MikroTik")

        db.session.commit()
        print("Seeding completed.")


if __name__ == "__main__":
    seed()
