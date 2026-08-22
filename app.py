import os

from flask import Flask

from models import db
from controller import admin_routes

# Used when SECRET_KEY is not in the environment. wsgi.py refuses to serve
# with this value still in place, so it can only ever be a local convenience.
DEV_SECRET = "dev-only-insecure-key-change-me"


def database_url():
    """Prefer DATABASE_URL so the app can move to Postgres without a code
    change; fall back to the SQLite file for local work."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return "sqlite:///tms.sqlite3"
    # Render and Heroku hand out the legacy postgres:// prefix, which
    # SQLAlchemy 2 no longer recognises.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url()

# Free hosts drop idle Postgres connections. Without pre-ping the first
# request after a quiet spell dies on a stale socket.
if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", DEV_SECRET)

# Session cookies: signed already, these stop them leaking or being read by
# scripts. SECURE is off for local http, on once a real host sets HTTPS=on.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("HTTPS", "").lower() in ("1", "on", "true")

db.init_app(app)

app.register_blueprint(admin_routes)

# Create the tables on first run so a fresh clone (or a fresh host) works
# without a manual step. Existing tables are left alone.
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Local development only — in production a WSGI server imports `app` from
    # wsgi.py, which never turns the debugger on. Debug is opt-in even here:
    # the Werkzeug console is remote code execution if it is ever reachable.
    app.run(
        debug = os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "on", "true"),
        port = int(os.environ.get("PORT", 5000)),
    )
