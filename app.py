from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from routes.services import services_bp

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
    weight = db.Column(db.Float)  # Weight in kg
    height = db.Column(db.Float)  # Height in cm
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    
    @property
    def bmi(self):
        """Calculate BMI if height and weight are available"""
        if self.height and self.weight and self.height > 0:
            # BMI formula: weight(kg) / (height(m))²
            height_in_meters = self.height / 100
            return round(self.weight / (height_in_meters * height_in_meters), 1)
        return None
    
    @property
    def bmi_category(self):
        """Return BMI category based on BMI value"""
        bmi_value = self.bmi
        if bmi_value is None:
            return None
        elif bmi_value < 18.5:
            return "Underweight"
        elif bmi_value < 25:
            return "Normal weight"
        elif bmi_value < 30:
            return "Overweight"
        else:
            return "Obese"

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
    
    date_filter = request.args.get('date_filter')
    specific_date = request.args.get('specific_date')
    
    today = datetime.now().date()
    
    if date_filter == 'today':
        filter_date = today
        date_display = "d'aujourd'hui"
    elif date_filter == 'tomorrow':
        filter_date = today + timedelta(days=1)
        date_display = "de demain"
    elif specific_date:
        filter_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
        date_display = f"du {filter_date.strftime('%d/%m/%Y')}"
    else:
        filter_date = today
        date_display = "d'aujourd'hui"
    
    appointments = Appointment.query.filter(
        func.date(Appointment.date) == filter_date
    ).order_by(Appointment.date).all()
    
    return render_template('dashboard.html', 
                         appointments=appointments,
                         date_display=date_display)

@app.route('/patients')
def patients():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    # Récupérer le terme de recherche depuis les paramètres GET
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Filtrer les patients par nom ou prénom
        all_patients = Patient.query.filter(
            (Patient.first_name.ilike(f"%{search_query}%")) |
            (Patient.last_name.ilike(f"%{search_query}%"))
        ).all()
    else:
        # Récupérer tous les patients si aucun terme de recherche
        all_patients = Patient.query.all()
    
    return render_template('patients.html', patients=all_patients)

@app.route('/patient/<int:patient_id>')
def patient_details(patient_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.date.desc()).all()
    
    # Add today's date to be used for age calculation
    today = datetime.now().date()
    
    return render_template('patient_details.html', patient=patient, appointments=appointments, today=today)

@app.route('/patient/add', methods=['GET', 'POST'])
def add_patient():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Validation de la date de naissance
            dob_str = request.form.get('date_of_birth')
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if dob > today:
                raise ValueError("La date de naissance ne peut pas être dans le futur")
            
            age = (today - dob).days // 365
            if age > 120:
                raise ValueError("Âge invalide")
            
            # Validation du poids et de la taille
            weight = request.form.get('weight')
            height = request.form.get('height')
            
            if weight:
                weight = float(weight)
                if not 0 <= weight <= 500:
                    raise ValueError("Le poids doit être compris entre 0 et 500 kg")
            
            if height:
                height = float(height)
                if not 0 <= height <= 300:
                    raise ValueError("La taille doit être comprise entre 0 et 300 cm")
            
            # Validation du numéro de téléphone
            phone = request.form.get('phone').replace(' ', '')
            if not phone.isdigit() or len(phone) < 8 or len(phone) > 15:
                raise ValueError("Numéro de téléphone invalide")
            
            new_patient = Patient(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                date_of_birth=dob,
                phone=phone,
                medical_history=request.form.get('medical_history'),
                weight=weight,
                height=height,
                first_consultation_diagnostic=request.form.get('first_consultation_diagnostic'),
                first_consultation_treatment=request.form.get('first_consultation_treatment'),
                first_consultation_notes=request.form.get('first_consultation_notes')
            )
            
            db.session.add(new_patient)
            db.session.commit()
            
            flash('Patient ajouté avec succès', 'success')
            return redirect(url_for('patients'))
            
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('add_patient.html')
        except Exception as e:
            flash('Une erreur est survenue lors de l\'ajout du patient', 'danger')
            return render_template('add_patient.html')
    
    return render_template('add_patient.html', today=datetime.now().date().isoformat())

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
    # Add new columns to the existing table
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text('ALTER TABLE patient ADD COLUMN weight FLOAT'))
            conn.execute(db.text('ALTER TABLE patient ADD COLUMN height FLOAT'))
            conn.commit()
        except Exception as e:
            # Columns might already exist
            print(f"Error during migration: {e}")
    
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

app.register_blueprint(services_bp, url_prefix='/services')

if __name__ == '__main__':
    app.run(debug=True)