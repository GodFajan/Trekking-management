from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class user(db.Model):
    user_id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String, nullable = False)
    email = db.Column(db.String, unique = True,nullable = False)
    password = db.Column(db.String, nullable = False)
    phone = db.Column(db.String, nullable = False)
    address = db.Column(db.String, nullable = False)
    role = db.Column(db.String, nullable = False)
    status = db.Column(db.String, nullable = False)

class trek(db.Model):
    trek_id = db.Column(db.Integer, primary_key = True)
    trek_name = db.Column(db.String, nullable = False)
    location = db.Column(db.String, nullable = False)
    difficulty = db.Column(db.String, nullable = False)
    duration_days = db.Column(db.Integer, nullable = False)
    available_slots = db.Column(db.Integer,  nullable = False)
    # ass_staff_id = db.Column(db.Integer, db.ForeignKey('user.user_id'),nullable = False)
    ass_staff_id = db.Column(db.Integer, nullable = False)
    status = db.Column(db.String, nullable = False)
    start_date = db.Column(db.Date, nullable = False)
    end_date = db.Column(db.Date, nullable = False)

class booking(db.Model):
    booking_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable = False)
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.trek_id'), nullable = False)
    booking_date = db.Column(db.Date, nullable = False)
    status = db.Column(db.String, nullable = False)        
