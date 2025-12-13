from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import bp
from app.models import User
from app.extensions import db
from app.utils.decorators import admin_required
from .forms import UserCreateForm, PasswordResetForm, EmptyForm

@bp.route("/users")
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.username).all()
    form = EmptyForm()
    return render_template("admin/users/list.html", users=users, form=form)

@bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "danger")
        return redirect(url_for("admin.list_users"))

    user.is_admin = not user.is_admin
    db.session.commit()

    flash(f"Admin status updated for {user.username}.", "success")
    return redirect(url_for("admin.list_users"))

@bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    form = PasswordResetForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Password reset successfully.", "success")
        return redirect(url_for("admin.list_users"))

    return render_template(
        "admin/users/reset_password.html",
        user=user,
        form=form
    )

@bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    form = UserCreateForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("User created successfully.", "success")
        return redirect(url_for("admin.list_users"))

    return render_template("admin/users/create.html", form=form)

