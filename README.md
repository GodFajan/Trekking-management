# Trekking Management

A trek booking platform built with Flask. Admins publish departures and assign
guides, staff manage their own treks and participants, users browse and book.

---

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py create-admin    # the only way to make an Admin account
python app.py
```

Then open <http://127.0.0.1:5000>.

`/register` deliberately only offers **User** and **Staff** — an Admin can
never be created through the web form, so a fresh install needs the CLI once.

```bash
python manage.py list-admins
python manage.py reset-password you@example.com
```

### Tests

```bash
python smoke_test.py     # end-to-end: every route, as every role
```

---

## Deploying it

The app is host-agnostic: everything that differs between your laptop and a
public server is read from the environment.

| Variable | Required in production | What it does |
|---|---|---|
| `SECRET_KEY` | **yes** | Signs the session cookie. `wsgi.py` refuses to boot without a real one. |
| `DATABASE_URL` | recommended | Any SQLAlchemy URL. Defaults to local SQLite. |
| `HTTPS` | recommended | Set to `on` once served over TLS, to mark cookies Secure. |
| `PORT` | no | Set by most hosts automatically. |

Generate a key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Option A — Render (gives you `https://trekking-company.onrender.com`)

[`render.yaml`](render.yaml) already describes the web service and a Postgres
database, so this is a two-click deploy.

1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → select the repo.
3. Render reads `render.yaml`, creates the service plus the database, and
   generates `SECRET_KEY` for you. Click **Apply**.
4. Once it is live, open the service's **Shell** tab and run:
   ```bash
   python manage.py create-admin
   ```
5. Sign in at `/login`.

Change the `name:` in `render.yaml` to change the subdomain.

Two things to know about the free plan: the service **sleeps after 15 minutes
idle**, so the first visit after a quiet spell takes ~50 seconds to wake; and
Render's free Postgres **expires after 30 days**. For something longer-lived,
create a free database at [neon.tech](https://neon.tech) instead and paste its
connection string into `DATABASE_URL`.

### Option B — PythonAnywhere (never sleeps, keeps SQLite)

Best if you want the app always warm and do not want to bother with Postgres —
PythonAnywhere has a persistent filesystem, so the SQLite file survives.

1. Sign up (free "Beginner" plan). Your URL is `yourusername.pythonanywhere.com`,
   so pick the username you want in the address.
2. **Bash console**:
   ```bash
   git clone https://github.com/GodFajan/Trekking-management
   cd Trekking-management
   mkvirtualenv --python=/usr/bin/python3.11 trek
   pip install -r requirements.txt
   ```
3. **Web tab** → Add a new web app → **Manual configuration** → Python 3.11.
4. Set *Source code* to `/home/YOURNAME/Trekking-management` and *Virtualenv*
   to `/home/YOURNAME/.virtualenvs/trek`.
5. Edit the WSGI configuration file it links to, replacing its contents with:
   ```python
   import sys
   sys.path.insert(0, "/home/YOURNAME/Trekking-management")
   from wsgi import app as application
   ```
6. In the Web tab's **Environment variables**, add `SECRET_KEY` and `HTTPS=on`.
7. Reload, then in the Bash console: `python manage.py create-admin`.

### Option C — a temporary link, straight off your machine

For a quick demo with no signup at all:

```bash
winget install cloudflare.cloudflared
python app.py
cloudflared tunnel --url http://localhost:5000     # in a second terminal
```

Prints a public `https://….trycloudflare.com` URL. It disappears when you stop
the command, and your PC has to stay on.

### A custom domain

A real `.com` is not free — `trekking-company.com` costs roughly $10–15/year
from Namecheap, Cloudflare or Porkbun. Once bought, both Render and
PythonAnywhere let you attach it (PythonAnywhere requires a paid plan for
custom domains; Render allows them on the free plan).

Genuinely free alternatives are subdomains: `trekking-company.onrender.com`
out of the box, or a `.is-a.dev` / `.js.org` subdomain by pull request.

---

## Security notes

- Passwords are hashed with `werkzeug.security`. Rows created before hashing
  was added are upgraded in place the next time that user signs in.
- `instance/` is gitignored — the database must never be committed.
- `wsgi.py` will not start with the development `SECRET_KEY` in place, and
  forces `debug` off regardless of environment.
