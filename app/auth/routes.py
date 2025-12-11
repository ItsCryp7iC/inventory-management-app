from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from . import bp
from .forms import LoginForm
from app.models import User


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in successfully.", "success")

            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
