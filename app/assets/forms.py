from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    TextAreaField,
    DateField,
    DecimalField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, Length



class AssetForm(FlaskForm):
    name = StringField("Asset Name", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional()])

    serial_number = StringField("Serial Number", validators=[Optional(), Length(max=150)])

    status = SelectField(
        "Status",
        choices=[
            ("in_use", "In Use"),
            ("in_stock", "In Stock"),
            ("under_repair", "Under Repair"),
            ("retired", "Retired"),
            ("disposed", "Disposed"),
        ],
        validators=[DataRequired()],
    )

    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    subcategory_id = SelectField("Sub-Category", coerce=int, validators=[Optional()])
    location_id = SelectField("Location", coerce=int, validators=[DataRequired()])
    
    purchase_date = DateField("Purchase Date", format="%Y-%m-%d", validators=[Optional()])
    warranty_expiry_date = DateField("Warranty Expiry Date", format="%Y-%m-%d", validators=[Optional()])
    cost = DecimalField("Cost", places=2, validators=[Optional()])
    vendor_id = SelectField("Vendor", coerce=int, validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])

    submit = SubmitField("Save")
