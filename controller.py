from flask import Blueprint, render_template, request, redirect, session
from models import *
from sqlalchemy import or_, cast, String
from datetime import date

admin_routes = Blueprint('admin_routes', __name__)

# Roles a visitor is allowed to self-register as. Anything else is rejected so
# a hand-crafted POST can't hand itself an Admin account.
SELF_SIGNUP_ROLES = ("User", "Staff")


def active_staffs():
    """Staff who are approved and not blacklisted — the assignable pool."""
    return db.session.query(user).filter(
        user.role == "Staff",
        user.status == "Active"
    ).order_by(user.name).all()


def staff_choices(current_staff_id=None):
    """Assignable staff, guaranteeing the trek's current staff stays listed.

    A staff member can be blacklisted after being assigned to a trek. If they
    dropped off the dropdown, editing that trek would silently reassign it to
    whoever happened to be first in the list.
    """
    staffs = active_staffs()
    if current_staff_id is not None and all(s.user_id != current_staff_id for s in staffs):
        current = user.query.get(current_staff_id)
        if current:
            staffs = [current] + staffs
    return staffs


def staff_name_map():
    """user_id -> name, so trek tables show a guide instead of a raw id."""
    return {s.user_id: s.name for s in db.session.query(user).filter(user.role == "Staff").all()}


@admin_routes.route("/")
def landing_page():
    return render_template("landing.html")

@admin_routes.route("/login", methods = ["GET", "POST"])
def signin():
    if request.method == "POST":
        user_email = request.form.get("emailid")
        user_password = request.form.get("pwd")
        tem_user = db.session.query(user).filter(user.email == user_email, user.password == user_password ).first()
        if tem_user:
            if tem_user.role == "Staff" and tem_user.status == "Pending":
                return render_template("login.html", err_msg_pending = "Your staff account is still waiting on admin approval.")
            if tem_user.status == "Blacklisted":
                return render_template("login.html", err_msg_blocked = "This account has been blacklisted. Please contact the admin.")
            session['user_role'] = tem_user.role
            session['user_id'] = tem_user.user_id
            session['user_name'] = tem_user.name
            if tem_user.role == "Admin":
                return redirect("/admin_login")
            if tem_user.role == "Staff":
                return redirect("/staff_login")
            if tem_user.role == "User":
                return redirect("/user_login")
        else:
            return render_template("login.html", err_msg = "That email and password combination did not match an account.")
    return render_template("login.html")

@admin_routes.route("/register", methods = ["GET", "POST"])
def signup():
    if request.method == "POST":
        user_email = request.form.get("emailid")
        password = request.form.get("pwd")
        user_name = request.form.get("fname")
        user_type = request.form.get("utype")
        user_address = request.form.get("address")
        user_phone = request.form.get("phno")
        if user_type not in SELF_SIGNUP_ROLES:
            return render_template("register.html", err_msg = "Please choose a valid account type.")
        if user_type == "Staff":
            user_status = "Pending"
        else:
            user_status = "Active"
        tem_user = db.session.query(user).filter(user.email == user_email).first()
        if tem_user:
            return render_template("register.html", err_msg = "That email is already registered - try signing in instead.")
        else:
            user_cred = user(email = user_email, password = password, name = user_name, role = user_type, address = user_address, phone = user_phone, status = user_status)
            db.session.add(user_cred)
            db.session.commit()
            session['reg_suc'] = True
            return redirect("/login")
    return render_template("register.html")

@admin_routes.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@admin_routes.route("/admin_login")
def admin_login():
    if session.get('user_role') != "Admin":
        return redirect("/login")
    total_treks = trek.query.count()
    total_users = user.query.filter_by(role = "User", status = "Active").count()
    total_staffs = user.query.filter_by(role = "Staff", status = "Active").count()
    total_booking = booking.query.count()
    pending_staffs = user.query.filter_by(role = "Staff", status = "Pending").count()
    return render_template("admin_dashboard.html", total_treks = total_treks, total_users = total_users, total_staffs = total_staffs, total_booking = total_booking, pending_staffs = pending_staffs)

@admin_routes.route("/staff_login")
def staff_login():
    if session.get('user_role') != "Staff":
        return redirect("/login")
    t_user = db.session.query(user).filter(user.user_id == session['user_id']).first()
    ass_treks = trek.query.filter_by(ass_staff_id = session['user_id']).count()
    open_treks = trek.query.filter_by(ass_staff_id = session['user_id'], status = 'Open').count()
    total_part = db.session.query(booking).join(trek, booking.trek_id == trek.trek_id).filter(trek.ass_staff_id == session['user_id']).count()
    assigned_treks = trek.query.filter_by(ass_staff_id=session['user_id']).all()
    trek_data = []
    for t in assigned_treks:
       participant_count = booking.query.filter_by(trek_id=t.trek_id).count()
       trek_data.append((t, participant_count))
    return render_template("staff_dashboard.html", t2_user = t_user, ass_treks = ass_treks, open_treks = open_treks, total_part = total_part,trek_data = trek_data)

@admin_routes.route("/user_login")
def userlogin():
    if session.get('user_role') != "User":
        return redirect("/login")
    t_user = db.session.query(user).filter(user.user_id == session['user_id']).first()
    my_bookings = db.session.query(booking, trek).join(trek, booking.trek_id == trek.trek_id).filter(booking.user_id == session['user_id']).all()
    return render_template("user_dashboard.html", t_user = t_user,my_bookings = my_bookings)


@admin_routes.route("/trek_add", methods = ["GET","POST"])
def trek_add():
    if session.get('user_role') != "Admin":
        return redirect("/login")

    if request.method == "POST":
        trek_name = request.form.get("tname")
        location = request.form.get("lname")
        difficulty = request.form.get("dfclty")
        status = request.form.get("stype")
        try:
            slots = int(request.form.get("slots"))
            staff_id = int(request.form.get("s_id"))
            start_date = date.fromisoformat(request.form.get("str_date"))
            end_date = date.fromisoformat(request.form.get("end_date"))
            cal_duration = (end_date - start_date).days + 1

            if start_date < date.today():
                # The min= attribute on the field is only a hint; a hand-made
                # POST would sail straight past it.
                session['err_msg_past_date'] = True
                return redirect("/trek_add")
            if cal_duration <= 0:
                session['err_msg_end_date'] = True
                return redirect("/trek_add")
            if slots < 0:
                session['err_msg_value_error'] = True
                return redirect("/trek_add")
        except(ValueError, TypeError):
            session['err_msg_value_error'] = True
            return redirect("/trek_add")
        trek_details = trek(
            trek_name = trek_name,
            location = location,
            difficulty = difficulty,
            duration_days = cal_duration,
            available_slots = slots,
            ass_staff_id = staff_id,
            status = status,
            start_date = start_date,
            end_date = end_date
        )
        db.session.add(trek_details)
        db.session.commit()
        session['added_trek'] = True
        return redirect("/admin_login")
    return render_template("trek_add.html", staffs = active_staffs(), today = date.today().isoformat())


@admin_routes.route("/all_treks", methods = ["GET"])
def all_treks():
    role = session.get("user_role")
    if role not in ("Admin", "User"):
        return redirect("/login")

    search_word = request.args.get("searchtrek", "").strip()

    query = db.session.query(trek)
    if role == "User":
        # Users only ever see open treks, so filter here rather than in the
        # template — otherwise a search matching only closed treks returns
        # rows that get hidden, and the page just looks empty.
        query = query.filter(trek.status == "Open")
    if search_word:
        pattern = f"%{search_word}%"
        query = query.filter(or_(
            trek.trek_name.ilike(pattern),
            trek.location.ilike(pattern),
            trek.difficulty.ilike(pattern),
            trek.status.ilike(pattern),
            cast(trek.duration_days, String).ilike(pattern),
            cast(trek.start_date, String).ilike(pattern)
        ))
    all_t = query.order_by(trek.start_date).all()

    if role == "Admin":
        return render_template('all_treks.html', all_t = all_t, search_word = search_word, staff_names = staff_name_map())
    # Mark treks this traveller already holds a booking on, so the Book button
    # can show as taken instead of failing on submit.
    booked_ids = {b.trek_id for b in booking.query.filter_by(user_id = session['user_id']).all()}
    return render_template("all_trek_user.html", all_t = all_t, search_word = search_word, staff_names = staff_name_map(), booked_ids = booked_ids)


@admin_routes.route("/edit_trek/<int:trek_id>", methods = ["GET", "POST"])
def edit_treks(trek_id):
    if session.get("user_role") != "Admin":
        return redirect("/login")
    t = trek.query.get(trek_id)
    if not t:
        return redirect("/all_treks")
    # A trek that already started keeps its real start date as the floor, so an
    # admin editing an old trek for any other reason isn't blocked by a rule
    # aimed at new departures.
    date_floor = min(t.start_date, date.today()).isoformat()

    def back(msg):
        return render_template("edit_trek.html", t = t,
                               staffs = staff_choices(t.ass_staff_id),
                               today = date_floor, err_msg = msg)

    if request.method == "GET":
        return render_template("edit_trek.html", t = t, staffs = staff_choices(t.ass_staff_id), today = date_floor)

    trek_name = request.form.get("tname")
    location = request.form.get("lname")
    difficulty = request.form.get("dfclty")
    status = request.form.get("stype")
    try:
        slots = int(request.form.get("slots"))
        staff_id = int(request.form.get("s_id"))
        start_date = date.fromisoformat(request.form.get("str_date"))
        end_date = date.fromisoformat(request.form.get("end_date"))
        cal_duration = (end_date - start_date).days + 1

        # Only reject a past start date when the admin actually moved it —
        # a trek that legitimately began last month must stay editable.
        if start_date != t.start_date and start_date < date.today():
            return back("Start date can't be in the past")
        if cal_duration <= 0:
            return back("End date can't be earlier than the start date")
        if slots < 0:
            return back("Available slots can't be negative")

    except(ValueError, TypeError):
        return back("Provide correct details")

    t.trek_name = trek_name
    t.location=location
    t.difficulty=difficulty
    t.duration_days=cal_duration
    t.available_slots=slots
    t.ass_staff_id=staff_id
    t.status=status
    t.start_date=start_date
    t.end_date=end_date
    db.session.commit()
    session['edited_trek'] = True
    return redirect("/admin_login")

@admin_routes.route("/delete_trek/<int:trek_id>", methods = ["POST"])
def delete_trek(trek_id):
    if session.get("user_role") != "Admin":
        return redirect("/login")
    t = trek.query.get(trek_id)
    if t:
        # Bookings carry a FK to this trek — clear them first so the delete
        # can't fail and no orphan rows are left behind.
        booking.query.filter_by(trek_id = trek_id).delete()
        db.session.delete(t)
        db.session.commit()
        session['del_suc'] = True
    return redirect("/admin_login")


@admin_routes.route("/all_staffs_users")
def all_staffs_users():
    if session.get("user_role") != "Admin":
        return redirect("/login")
    search_word = request.args.get("searchuser", "").strip()

    # Admins are never listed, so exclude them in the query — filtering them
    # out in the template would make a search for "Admin" look like a miss.
    query = db.session.query(user).filter(user.role != "Admin")
    if search_word:
        pattern = f"%{search_word}%"
        query = query.filter(or_(
            user.name.ilike(pattern),
            user.email.ilike(pattern),
            user.phone.ilike(pattern),
            user.role.ilike(pattern),
            user.address.ilike(pattern),
            cast(user.user_id, String).ilike(pattern),
        ))
    all_u = query.all()

    # Split by status here so each table can show its own empty state.
    return render_template(
        "all_staffs_users.html",
        active_u = [u for u in all_u if u.status == "Active"],
        blocked_u = [u for u in all_u if u.status == "Blacklisted"],
        pending_u = [u for u in all_u if u.status == "Pending"],
        search_word = search_word
    )


@admin_routes.route("/blacklist/<int:user_id>", methods = ["POST"])
def blacklist(user_id):
    if session.get("user_role") != "Admin":
        return redirect("/login")
    u = user.query.get(user_id)
    if u:
        u.status = "Blacklisted"
        db.session.commit()
        session['blk_suc'] = True
    return redirect("/all_staffs_users")

@admin_routes.route("/approve/<int:user_id>", methods = ["POST"])
def approve(user_id):
    if session.get('user_role') != "Admin":
        return redirect("/login")
    u = user.query.get(user_id)
    if u:
        u.status = "Active"
        db.session.commit()
        session['app_suc'] = True
    return redirect("/all_staffs_users")

@admin_routes.route("/reject/<int:user_id>", methods = ["POST"])
def reject(user_id):
    if session.get('user_role') != "Admin":
        return redirect("/login")
    u = user.query.get(user_id)
    if u:
        booking.query.filter_by(user_id = user_id).delete()
        db.session.delete(u)
        db.session.commit()
        session['rej_suc'] = True
    return redirect("/all_staffs_users")

@admin_routes.route("/book_trek/<int:trek_id>", methods = ["POST"])
def book_trek(trek_id):
    if session.get('user_role') != "User":
        return redirect("/login")
    t = trek.query.get(trek_id)
    if (not t) or (t.status != "Open") or (t.available_slots <= 0):
        session['book_err'] = True
        return redirect("/all_treks")

    already = booking.query.filter_by(user_id = session['user_id'], trek_id = trek_id).first()
    if already:
        session['book_dup'] = True
        return redirect("/all_treks")

    booking_details = booking(
        user_id = session['user_id'],
        trek_id = trek_id,
        booking_date = date.today(),
        status = "Booked"
    )
    db.session.add(booking_details)
    t.available_slots -= 1
    if t.available_slots <= 0:
        t.status = "Closed"
    db.session.commit()
    session['book_suc'] = True
    return redirect("/all_treks")


@admin_routes.route("/staff_mng/<int:trek_id>", methods=["GET", "POST"])
def staff_mng(trek_id):
    if session.get('user_role') != "Staff":
        return redirect("/login")

    t = trek.query.get(trek_id)
    if not t or t.ass_staff_id != session['user_id']:
        return redirect("/staff_login")

    if request.method == "POST":
        try:
            new_slots = int(request.form.get("Aslots"))
            if new_slots < 0:
                raise ValueError
        except (ValueError, TypeError):
            session['mng_err'] = True
            return redirect(f"/staff_mng/{trek_id}")
        t.available_slots = new_slots
        t.status = request.form.get("stype")
        db.session.commit()
        session['mng_suc'] = True
        return redirect(f"/staff_mng/{trek_id}")

    participants = db.session.query(booking, user).join(user, booking.user_id == user.user_id).filter(booking.trek_id == trek_id).all()
    return render_template("staff_mng.html", t=t, participants=participants)


@admin_routes.route("/mark_completed/<int:trek_id>", methods=["POST"])
def mark_completed(trek_id):
    if session.get('user_role') != "Staff":
        return redirect("/login")

    t = trek.query.get(trek_id)
    if not t or t.ass_staff_id != session['user_id']:
        return redirect("/staff_login")

    t.status = "Completed"
    # Close out every booking on the trek too, otherwise a traveller's
    # "Booking History" table never fills up.
    for b in booking.query.filter_by(trek_id = trek_id).all():
        b.status = "Completed"
    db.session.commit()
    session['comp_suc'] = True
    return redirect(f"/staff_mng/{trek_id}")
