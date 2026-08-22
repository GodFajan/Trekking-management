"""Command-line helpers that have no place in the web UI.

  python manage.py create-admin
  python manage.py create-admin --email me@x.com --name "Ada" --password s3cret
  python manage.py list-admins
  python manage.py reset-password me@x.com

An Admin cannot be made through /register on purpose — the signup form only
offers User and Staff — so a fresh deployment needs this once.
"""
import argparse
import getpass
import sys

from werkzeug.security import generate_password_hash

from app import app
from models import db, user


def create_admin(args):
    email = args.email or input("Admin email: ").strip()
    name = args.name or input("Full name: ").strip()
    password = args.password or getpass.getpass("Password (min 8 chars): ")

    if not email or not name:
        sys.exit("Email and name are both required.")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")

    with app.app_context():
        if user.query.filter_by(email=email).first():
            sys.exit("An account with %s already exists." % email)
        db.session.add(user(
            email=email,
            password=generate_password_hash(password),
            name=name,
            role="Admin",
            address=args.address,
            phone=args.phone,
            status="Active",
        ))
        db.session.commit()
    print("Admin created: %s — sign in at /login" % email)


def list_admins(args):
    with app.app_context():
        admins = user.query.filter_by(role="Admin").order_by(user.user_id).all()
        if not admins:
            print("No admin accounts exist. Run: python manage.py create-admin")
            return
        for a in admins:
            print("  #%-4d %-32s %s" % (a.user_id, a.email, a.name))


def reset_password(args):
    password = args.password or getpass.getpass("New password (min 8 chars): ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")
    with app.app_context():
        u = user.query.filter_by(email=args.email).first()
        if not u:
            sys.exit("No account with email %s" % args.email)
        u.password = generate_password_hash(password)
        db.session.commit()
    print("Password reset for %s" % args.email)


parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
sub = parser.add_subparsers(dest="command", required=True)

p = sub.add_parser("create-admin", help="create an Admin account")
p.add_argument("--email")
p.add_argument("--name")
p.add_argument("--password", help="omit to be prompted without echo")
p.add_argument("--address", default="-")
p.add_argument("--phone", default="-")
p.set_defaults(func=create_admin)

p = sub.add_parser("list-admins", help="show existing Admin accounts")
p.set_defaults(func=list_admins)

p = sub.add_parser("reset-password", help="set a new password for an account")
p.add_argument("email")
p.add_argument("--password")
p.set_defaults(func=reset_password)

if __name__ == "__main__":
    args = parser.parse_args()
    args.func(args)
