from flask import Flask
from models import db
from controller import admin_routes

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tms.sqlite3"
app.config["SECRET_KEY"] = "any-random-string"

db.init_app(app)

app.register_blueprint(admin_routes)

# Create the tables on first run so a fresh clone works without a manual step.
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug = True)
