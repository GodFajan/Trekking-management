"""Throwaway end-to-end smoke test: exercises every route as every role.

Run with:  python smoke_test.py
Uses its own temp sqlite file, so the real instance/tms.sqlite3 is untouched.
"""
import os
import tempfile
from datetime import date, timedelta

from flask import Flask
from models import db, user, trek, booking
from controller import admin_routes

fd, dbpath = tempfile.mkstemp(suffix=".sqlite3")
os.close(fd)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + dbpath.replace("\\", "/")
app.config["SECRET_KEY"] = "test"
db.init_app(app)
app.register_blueprint(admin_routes)

FAILS = []
CHECKS = [0]


def check(label, cond, extra=""):
    CHECKS[0] += 1
    if cond:
        print("  ok   " + label)
    else:
        print("  FAIL " + label + (" :: " + str(extra) if extra else ""))
        FAILS.append(label)


def page(c, path, expect=200):
    r = c.get(path)
    check("GET %s -> %s" % (path, r.status_code), r.status_code == expect,
          r.status_code)
    return r


def login(c, email, pwd="pw"):
    return c.post("/login", data={"emailid": email, "pwd": pwd},
                  follow_redirects=False)


with app.app_context():
    db.create_all()
    db.session.add_all([
        user(name="Root Admin", email="admin@x.com", password="pw", phone="1",
             address="a", role="Admin", status="Active"),
        user(name="Bina Guide", email="staff@x.com", password="pw", phone="2",
             address="a", role="Staff", status="Active"),
        user(name="Pending Pat", email="pend@x.com", password="pw", phone="3",
             address="a", role="Staff", status="Pending"),
        user(name="Blocked Bob", email="blk@x.com", password="pw", phone="4",
             address="a", role="User", status="Blacklisted"),
        user(name="Tara Walker", email="user@x.com", password="pw", phone="5",
             address="a", role="User", status="Active"),
    ])
    db.session.commit()
    staff_id = user.query.filter_by(email="staff@x.com").first().user_id

print("\n=== anonymous ===")
with app.test_client() as c:
    page(c, "/")
    page(c, "/login")
    page(c, "/register")
    for guarded in ("/admin_login", "/staff_login", "/user_login",
                    "/all_treks", "/trek_add", "/all_staffs_users"):
        r = c.get(guarded)
        check("anon blocked from %s" % guarded, r.status_code == 302, r.status_code)

print("\n=== auth edge cases ===")
with app.test_client() as c:
    r = login(c, "admin@x.com", "wrong")
    check("bad password renders login (not a redirect)", r.status_code == 200)
    check("bad password shows a message", b"did not match" in r.data)
    r = login(c, "pend@x.com")
    check("pending staff blocked", b"waiting on admin approval" in r.data)
    r = login(c, "blk@x.com")
    check("blacklisted blocked", b"blacklisted" in r.data)
    r = c.post("/register", data={"emailid": "h@x.com", "pwd": "p",
                                  "fname": "Hax", "utype": "Admin",
                                  "address": "a", "phno": "9"})
    check("cannot self-register as Admin", b"valid account type" in r.data)
    with app.app_context():
        check("no Admin was created", user.query.filter_by(email="h@x.com").first() is None)

print("\n=== admin ===")
with app.test_client() as c:
    login(c, "admin@x.com")
    r = page(c, "/admin_login")
    check("KPI numbers render (not blank)", b"<td>0</td>" in r.data or b"<td>1</td>" in r.data)
    page(c, "/trek_add")
    r = c.get("/trek_add")
    check("staff dropdown lists the active staff by name", b"Bina Guide" in r.data)
    check("staff dropdown excludes pending staff", b"Pending Pat" not in r.data)
    check("no raw staff-id text input", b'name="s_id" id="s_id" required>' not in r.data or b"<select" in r.data)

    today = date.today()
    r = c.post("/trek_add", data={
        "tname": "Kedarkantha", "lname": "Uttarakhand", "dfclty": "Moderate",
        "stype": "Open", "slots": "2", "s_id": str(staff_id),
        "str_date": today.isoformat(),
        "end_date": (today + timedelta(days=4)).isoformat()},
        follow_redirects=True)
    check("trek added", b"Trek added successfully" in r.data)
    with app.app_context():
        t = trek.query.filter_by(trek_name="Kedarkantha").first()
        check("duration computed", t is not None and t.duration_days == 5,
              t.duration_days if t else None)
        tid = t.trek_id

    r = c.post("/trek_add", data={
        "tname": "Bad", "lname": "L", "dfclty": "Easy", "stype": "Open",
        "slots": "3", "s_id": str(staff_id),
        "str_date": today.isoformat(),
        "end_date": (today - timedelta(days=3)).isoformat()},
        follow_redirects=True)
    check("bad end date is reported", b"correct end date" in r.data)

    r = c.post("/trek_add", data={
        "tname": "Bad2", "lname": "L", "dfclty": "Easy", "stype": "Open",
        "slots": "abc", "s_id": str(staff_id),
        "str_date": today.isoformat(),
        "end_date": (today + timedelta(days=1)).isoformat()},
        follow_redirects=True)
    check("non-numeric slots is reported", b"correct details" in r.data)

    r = c.post("/trek_add", data={
        "tname": "Past", "lname": "L", "dfclty": "Easy", "stype": "Open",
        "slots": "3", "s_id": str(staff_id),
        "str_date": (today - timedelta(days=10)).isoformat(),
        "end_date": (today + timedelta(days=1)).isoformat()},
        follow_redirects=True)
    check("past start date refused by the server", b"can't start in the past" in r.data)
    with app.app_context():
        check("no past-dated trek was created",
              trek.query.filter_by(trek_name="Past").first() is None)
    r = c.get("/trek_add")
    check("start-date field carries min=today",
          ('min="%s"' % today.isoformat()).encode() in r.data)

    r = page(c, "/all_treks")
    check("trek list shows the guide name", b"Bina Guide" in r.data)
    r = c.get("/all_treks?searchtrek=kedar")
    check("search finds a partial, case-insensitive match", b"Kedarkantha" in r.data)
    r = c.get("/all_treks?searchtrek=uttarakhand")
    check("search matches on location too", b"Kedarkantha" in r.data)
    r = c.get("/all_treks?searchtrek=zzzz")
    check("no match shows an empty state", b"No treks match" in r.data)
    r = c.get("/all_treks?searchtrek=")
    check("empty search shows everything", b"Kedarkantha" in r.data)

    r = page(c, "/edit_trek/%d" % tid)
    check("edit page preselects the assigned staff", b"selected" in r.data)
    r = c.post("/edit_trek/%d" % tid, data={
        "tname": "Kedarkantha", "lname": "Uttarakhand", "dfclty": "Moderate",
        "stype": "Open", "slots": "2", "s_id": str(staff_id),
        "str_date": (today - timedelta(days=5)).isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat()})
    check("edit refuses moving the start date into the past",
          b"can&#39;t be in the past" in r.data or b"can't be in the past" in r.data)

    r = c.get("/edit_trek/999999")
    check("edit of a missing trek redirects (no crash)", r.status_code == 302)

    r = page(c, "/all_staffs_users")
    check("pending staff listed", b"Pending Pat" in r.data)
    check("admin row itself is not listed in the table",
          b"<td>Root Admin</td>" not in r.data)
    r = c.get("/all_staffs_users?searchuser=Admin")
    check("searching 'Admin' gives a clean empty state", b"No active" in r.data)
    r = c.get("/all_staffs_users?searchuser=bina")
    check("user search works", b"Bina Guide" in r.data)

print("\n=== user booking ===")
with app.test_client() as c:
    login(c, "user@x.com")
    page(c, "/user_login")
    r = page(c, "/all_treks")
    check("user sees open trek", b"Kedarkantha" in r.data)
    check("user page has no Delete control", b"/delete_trek" not in r.data)
    r = c.post("/book_trek/%d" % tid, follow_redirects=True)
    check("booking succeeds (no AttributeError)", b"slot is confirmed" in r.data)
    with app.app_context():
        t = trek.query.get(tid)
        check("slots decremented 2 -> 1", t.available_slots == 1, t.available_slots)
        check("booking row created", booking.query.filter_by(trek_id=tid).count() == 1)
    r = c.post("/book_trek/%d" % tid, follow_redirects=True)
    check("double booking refused", b"already booked" in r.data)
    with app.app_context():
        check("slots unchanged after refusal", trek.query.get(tid).available_slots == 1)
    r = page(c, "/user_login")
    check("booking shows under My Bookings", b"Kedarkantha" in r.data)
    check("history shows its empty state", b"No completed treks yet" in r.data)

print("\n=== staff management ===")
with app.test_client() as c:
    login(c, "staff@x.com")
    r = page(c, "/staff_login")
    check("assigned-trek slot count renders", b"<td>1</td>" in r.data)
    r = page(c, "/staff_mng/%d" % tid)
    check("slots field is populated", b'value="1"' in r.data)
    check("participant listed", b"Tara Walker" in r.data)
    r = c.post("/staff_mng/%d" % tid, data={"Aslots": "7", "stype": "Open"},
               follow_redirects=True)
    check("slot update reports success", b"updated successfully" in r.data)
    with app.app_context():
        check("slot update PERSISTED 1 -> 7", trek.query.get(tid).available_slots == 7,
              trek.query.get(tid).available_slots)
    r = c.post("/staff_mng/%d" % tid, data={"Aslots": "oops", "stype": "Open"},
               follow_redirects=True)
    check("bad slot value is reported, not a 500", b"whole number" in r.data)
    r = c.post("/mark_completed/%d" % tid, follow_redirects=True)
    check("mark completed works", b"marked as completed" in r.data)
    with app.app_context():
        check("trek is Completed", trek.query.get(tid).status == "Completed")
        check("its bookings are Completed too",
              booking.query.filter_by(trek_id=tid).first().status == "Completed")
    r = page(c, "/staff_mng/%d" % tid)
    check("Completed is a real option in the status select",
          b'value="Completed" selected' in r.data)

print("\n=== history now populated, and logout ===")
with app.test_client() as c:
    login(c, "user@x.com")
    r = page(c, "/user_login")
    check("completed trek appears in Booking History", b"Kedarkantha" in r.data)
    r = c.get("/logout")
    check("logout redirects", r.status_code == 302)
    r = c.get("/admin_login")
    check("session really cleared", r.status_code == 302)

print("\n=== cascade on delete ===")
with app.test_client() as c:
    login(c, "admin@x.com")
    c.post("/delete_trek/%d" % tid, follow_redirects=True)
    with app.app_context():
        check("trek deleted", trek.query.get(tid) is None)
        check("its bookings deleted with it",
              booking.query.filter_by(trek_id=tid).count() == 0)

with app.app_context():
    db.session.remove()
    db.engine.dispose()
try:
    os.unlink(dbpath)
except OSError:
    pass

print("\n" + "=" * 52)
print("%d checks, %d failed" % (CHECKS[0], len(FAILS)))
for f in FAILS:
    print("  FAILED: " + f)
print("=" * 52)
raise SystemExit(1 if FAILS else 0)
