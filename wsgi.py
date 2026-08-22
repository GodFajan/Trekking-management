"""WSGI entry point — this is what a real host imports.

    gunicorn wsgi:app              (Render, Railway, Fly, any Linux host)

Importing through here rather than app.py directly buys two things:

  * the debugger can never be switched on, whatever the environment says;
  * the app refuses to boot at all if SECRET_KEY was left at its dev value,
    so a deploy fails loudly instead of quietly serving forgeable sessions.

PythonAnywhere: point its WSGI config file at this module, e.g.

    import sys
    sys.path.insert(0, "/home/YOURNAME/Trekking-management")
    from wsgi import app as application
"""
import os

from app import app, DEV_SECRET

if app.config["SECRET_KEY"] == DEV_SECRET:
    raise RuntimeError(
        "SECRET_KEY is still the development placeholder.\n"
        "Set a real one in the host's environment variables before serving:\n"
        '    python -c "import secrets; print(secrets.token_hex(32))"\n'
        "Without it anyone who has read this repo can forge a session cookie "
        "that says they are an Admin."
    )

# Belt and braces: gunicorn never reads __main__, but if anything ever does,
# it must not get the interactive debugger.
app.debug = False
app.config["DEBUG"] = False

if not os.environ.get("HTTPS"):
    # Not fatal — a host may terminate TLS without telling us — but the
    # session cookie will be sent over plain HTTP until this is set.
    app.logger.warning(
        "HTTPS is not set, so SESSION_COOKIE_SECURE is off. "
        "Set HTTPS=on once the site is served over https://"
    )

application = app  # PythonAnywhere and mod_wsgi look for this name
