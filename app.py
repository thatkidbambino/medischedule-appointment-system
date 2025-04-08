from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'thisisasecretkey'

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'medisched.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure DB exists on every startup (even in production)
with app.app_context():
    if not os.path.exists(os.path.join(basedir, 'database')):
        os.makedirs(os.path.join(basedir, 'database'))
    if not os.path.exists(db_path):
        db.create_all()
        print('✅ Database created!')

# ==============================
# Database Models
# ==============================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.String(300))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ==============================
# Login Loader
# ==============================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==============================
# Routes
# ==============================
@app.route('/')
def home():
    return redirect(url_for('login'))  # Redirect users to login instead of blank home.html

@app.route('/dashboard')
@login_required
def dashboard():
    appointments = Appointment.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', appointments=appointments)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        date = request.form.get('date')
        time = request.form.get('time')
        reason = request.form.get('reason')

        new_appointment = Appointment(
            patient_name=patient_name,
            date=date,
            time=time,
            reason=reason,
            user_id=current_user.id
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('appointments.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if appointment.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        appointment.patient_name = request.form.get('patient_name')
        appointment.date = request.form.get('date')
        appointment.time = request.form.get('time')
        appointment.reason = request.form.get('reason')
        db.session.commit()
        flash('Appointment updated successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('appointments.html', appointment=appointment)

@app.route('/delete/<int:id>')
@login_required
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if appointment.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment canceled.', 'info')
    return redirect(url_for('dashboard'))

