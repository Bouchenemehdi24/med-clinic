from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'doctor', 'staff'
    
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    medical_history = db.Column(db.Text)
    appointments = db.relationship('Appointment', backref='patient', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')  # 'scheduled', 'completed', 'cancelled'
    doctor = db.relationship('User', backref='appointments')

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.name
        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('dashboard'))
    
    flash('Invalid username or password', 'danger')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    today_appointments = Appointment.query.filter(
        Appointment.doctor_id == session['user_id'],
        Appointment.date.between(
            datetime.now().replace(hour=0, minute=0, second=0),
            datetime.now().replace(hour=23, minute=59, second=59)
        )
    ).all()
    
    return render_template('dashboard.html', 
                          appointments=today_appointments,
                          user_name=session['user_name'])

@app.route('/patients')
def patients():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    all_patients = Patient.query.all()
    return render_template('patients.html', patients=all_patients)

@app.route('/patient/<int:patient_id>')
def patient_details(patient_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.date.desc()).all()
    
    return render_template('patient_details.html', patient=patient, appointments=appointments)

@app.route('/patient/add', methods=['GET', 'POST'])
def add_patient():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        dob_str = request.form.get('date_of_birth')
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        
        new_patient = Patient(
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            date_of_birth=dob,
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            medical_history=request.form.get('medical_history')
        )
        
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Patient added successfully', 'success')
        return redirect(url_for('patients'))
    
    return render_template('add_patient.html')

@app.route('/appointments')
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == session['user_id'],
        Appointment.date >= datetime.now()
    ).order_by(Appointment.date).all()
    
    return render_template('appointments.html', appointments=upcoming_appointments)

@app.route('/appointment/add', methods=['GET', 'POST'])
def add_appointment():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        
        appointment_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        
        new_appointment = Appointment(
            patient_id=patient_id,
            doctor_id=session['user_id'],
            date=appointment_datetime,
            reason=request.form.get('reason'),
            notes=request.form.get('notes')
        )
        
        db.session.add(new_appointment)
        db.session.commit()
        
        flash('Appointment scheduled successfully', 'success')
        return redirect(url_for('appointments'))
    
    patients = Patient.query.all()
    return render_template('add_appointment.html', patients=patients)

@app.route('/appointment/<int:appointment_id>/update', methods=['GET', 'POST'])
def update_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if request.method == 'POST':
        appointment.status = request.form.get('status')
        appointment.notes = request.form.get('notes')
        
        db.session.commit()
        
        flash('Appointment updated successfully', 'success')
        return redirect(url_for('appointments'))
    
    return render_template('update_appointment.html', appointment=appointment)

# Initialize the database
with app.app_context():
    db.create_all()
    
    # Create a default admin user if no users exist
    if not User.query.first():
        default_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            name='Admin User',
            role='doctor'
        )
        db.session.add(default_user)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)