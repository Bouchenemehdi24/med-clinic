from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from functools import wraps
import pdfkit
from docx import Document
from docx.shared import Pt, Cm
from io import BytesIO
import io
import csv
from routes.services import services_bp  # Make sure this line is present

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.template_filter('nl2br')
def nl2br(value):
    if not value:
        return ''
    return value.replace('\n', '<br>').replace('\r', '')

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'doctor' ou 'assistant'
    speciality = db.Column(db.String(100))  # Augmenté à 100 caractères pour plus de flexibilité
    
    @property
    def is_doctor(self):
        return self.role == 'doctor'
    
    @property
    def is_assistant(self):
        return self.role == 'assistant'

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20))
    medical_history = db.Column(db.Text)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    diagnostic = db.Column(db.Text)
    treatment = db.Column(db.Text)
    next_appointment_date = db.Column(db.DateTime, nullable=True)
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    symptoms = db.Column(db.Text)  # Add this line
    
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
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    temp_patient_id = db.Column(db.Integer, db.ForeignKey('temporary_patient.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(50), nullable=False)  # Changed from Text to String(50)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')  # 'scheduled', 'completed', 'cancelled'
    doctor = db.relationship('User', backref='appointments')
    consultation = db.relationship('Consultation', backref=db.backref('appointment', uselist=False), uselist=False)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    symptoms = db.Column(db.Text)
    diagnostic = db.Column(db.Text)
    treatment = db.Column(db.Text)
    notes = db.Column(db.Text)
    follow_up_needed = db.Column(db.Boolean, default=False)
    next_appointment_date = db.Column(db.Date, nullable=True)
    consultation_order = db.Column(db.Integer, nullable=False)  # 1 = première consultation, 2+ = suivis

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    services = db.Column(db.JSON)  # Liste des services fournis
    paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime)
    consultation = db.relationship('Consultation', backref='payment', uselist=False)

class TemporaryPatient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='temp_patient', lazy=True,
                                 foreign_keys='Appointment.temp_patient_id')

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), nullable=False, default='Clinique Médicale')
    logo_url = db.Column(db.String(200))
    clinic_address = db.Column(db.Text)  # Ajout de l'adresse
    primary_color = db.Column(db.String(20), default='#0d6efd')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_settings():
        settings = AppSettings.query.first()
        if not settings:
            settings = AppSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

@app.context_processor
def inject_settings():
    return {'app_settings': AppSettings.get_settings()}

APPOINTMENT_REASONS = [
    'Toux',
    'Difficultés respiratoires',
    'Asthme',
    'Bronchite',
    'Allergie respiratoire',
    'BPCO',
    'Infection respiratoire',
    'Pneumonie suspectée',
    'Suivi respiratoire',
    'Autre symptôme respiratoire'
]

SYMPTOMES = {
    'Respiratoire': [
        'Toux sèche',
        'Toux grasse productive',
        'Toux nocturne',
        'Toux chronique (>3 semaines)',
        'Expectorations claires',
        'Expectorations verdâtres',
        'Expectorations jaunâtres',
        'Expectorations sanglantes',
        'Dyspnée légère',
        'Dyspnée modérée',
        'Dyspnée sévère',
        'Dyspnée au repos',
        'Dyspnée à l\'effort',
        'Dyspnée nocturne',
        'Dyspnée paroxystique',
        'Sifflements expiratoires',
        'Sifflements inspiratoires',
        'Wheezing',
        'Stridor',
        'Douleur thoracique respiratoire',
        'Douleur pleurale',
        'Oppression thoracique',
        'Respiration sifflante',
        'Respiration rapide (tachypnée)',
        'Respiration lente (bradypnée)',
        'Tirage intercostal',
        'Cyanose des lèvres',
        'Cyanose des extrémités',
        'Orthopnée',
        'Rhinorrhée',
        'Congestion nasale',
        'Éternuements fréquents',
        'Épistaxis',
        'Voix rauque',
        'Hémoptysie minime',
        'Hémoptysie massive'
    ],
    'Cardiovasculaire': [
        'Palpitations',
        'Douleur thoracique à l\'effort',
        'Douleur thoracique au repos',
        'Œdème des membres inférieurs',
        'Tachycardie (>100 bpm)',
        'Bradycardie (<60 bpm)',
        'Hypertension artérielle',
        'Hypotension artérielle',
        'Cyanose',
        'Syncope'
    ],
    'Digestif': [
        'Nausées légères',
        'Nausées sévères',
        'Vomissements alimentaires',
        'Vomissements bilieux',
        'Diarrhée aqueuse',
        'Diarrhée glairo-sanglante',
        'Constipation',
        'Douleur abdominale diffuse',
        'Douleur abdominale localisée',
        'Ballonnements'
    ],
    'Neurologique': [
        'Céphalées légères',
        'Céphalées intenses',
        'Migraine',
        'Vertiges',
        'Troubles de l\'équilibre',
        'Tremblements',
        'Convulsions',
        'Troubles de la conscience',
        'Troubles de la mémoire',
        'Troubles du langage'
    ],
    'Musculo-squelettique': [
        'Douleurs articulaires diffuses',
        'Douleurs articulaires localisées',
        'Raideur matinale',
        'Faiblesse musculaire',
        'Crampes musculaires',
        'Lombalgies',
        'Cervicalgies',
        'Sciatalgie',
        'Gonflement articulaire',
        'Limitation des mouvements'
    ],
    'Cutané': [
        'Éruption cutanée localisée',
        'Éruption cutanée généralisée',
        'Prurit',
        'Urticaire',
        'Eczéma',
        'Pétéchies',
        'Ecchymoses',
        'Œdème localisé',
        'Lésions ulcérées',
        'Modifications des ongles'
    ],
    'Général': [
        'Fièvre légère (37.5-38.5°C)',
        'Fièvre modérée (38.5-39.5°C)',
        'Fièvre intense (>39.5°C)',
        'Fatigue légère',
        'Fatigue intense',
        'Perte d\'appétit',
        'Perte de poids involontaire',
        'Sueurs nocturnes',
        'Malaise général',
        'Troubles du sommeil'
    ],
    'Psychologique': [
        'Anxiété légère',
        'Anxiété sévère',
        'Dépression',
        'Troubles du sommeil',
        'Irritabilité',
        'Troubles de la concentration',
        'Agitation',
        'Apathie',
        'Idées noires',
        'Attaques de panique'
    ]
}

DIAGNOSTICS = {
    'Respiratoire': [
        # Maladies obstructives
        'Asthme bronchique léger',
        'Asthme bronchique modéré',
        'Asthme bronchique sévère',
        'Asthme avec hyperréactivité bronchique',
        'BPCO légère',
        'BPCO modérée',
        'BPCO sévère',
        'Emphysème pulmonaire',
        'Bronchectasies',
        
        # Infections respiratoires
        'Bronchite aiguë',
        'Bronchite chronique simple',
        'Bronchite chronique mucopurulente',
        'Pneumonie communautaire',
        'Pneumonie atypique',
        'Pneumonie nosocomiale',
        'Bronchopneumonie',
        'Pleurésie infectieuse',
        'Abcès pulmonaire',
        'Tuberculose pulmonaire active',
        'Tuberculose pulmonaire latente',
        
        # Maladies restrictives
        'Fibrose pulmonaire idiopathique',
        'Pneumopathie interstitielle diffuse',
        'Sarcoïdose pulmonaire',
        'Pneumoconiose',
        'Asbestose',
        'Silicose',
        
        # Pathologies pleurales
        'Pneumothorax spontané',
        'Pneumothorax traumatique',
        'Pleurésie sérofibrineuse',
        'Épanchement pleural',
        'Hémothorax',
        'Chylothorax',
        
        # Pathologies vasculaires
        'Embolie pulmonaire aiguë',
        'Hypertension artérielle pulmonaire',
        'Cœur pulmonaire chronique',
        'Syndrome de détresse respiratoire aiguë (SDRA)',
        
        # Tumeurs
        'Cancer bronchique primitif',
        'Carcinome bronchique à petites cellules',
        'Carcinome bronchique non à petites cellules',
        'Métastases pulmonaires',
        'Tumeur carcinoïde bronchique',
        
        # Maladies des voies aériennes supérieures
        'Rhinite allergique persistante',
        'Rhinite allergique intermittente',
        'Sinusite maxillaire aiguë',
        'Sinusite chronique',
        'Polypose nasosinusienne',
        'Laryngite aiguë',
        'Laryngite chronique',
        'Dysfonction des cordes vocales',
        
        # Troubles respiratoires du sommeil
        'Syndrome d\'apnées du sommeil',
        'Syndrome d\'apnées-hypopnées obstructives',
        'Syndrome d\'apnées centrales',
        'Syndrome obesity-hypoventilation',
        
        # Maladies professionnelles
        'Asthme professionnel',
        'Bronchite chronique professionnelle',
        'Bérylliose',
        'Pneumopathie d\'hypersensibilité',
        
        # Autres pathologies
        'Mucoviscidose',
        'Dyskinésie ciliaire primitive',
        'Déficit en alpha-1 antitrypsine',
        'Protéinose alvéolaire',
        'Lymphangioléiomyomatose'
    ],
    'Cardiologie': [
        'Hypertension artérielle',
        'Insuffisance cardiaque',
        'Cardiopathie ischémique',
        'Angine de poitrine',
        'Infarctus du myocarde',
        'Trouble du rythme cardiaque',
        'Fibrillation auriculaire',
        'Péricardite',
        'Endocardite',
        'Thrombose veineuse profonde'
    ],
    'Gastroentérologie': [
        'Gastrite aiguë',
        'Gastrite chronique',
        'Ulcère gastrique',
        'Reflux gastro-œsophagien',
        'Colopathie fonctionnelle',
        'Maladie de Crohn',
        'Rectocolite hémorragique',
        'Hépatite virale',
        'Cirrhose hépatique',
        'Pancréatite aiguë'
    ],
    'Endocrinologie': [
        'Diabète type 1',
        'Diabète type 2',
        'Hypothyroïdie',
        'Hyperthyroïdie',
        'Maladie de Basedow',
        'Thyroïdite',
        'Obésité',
        'Syndrome métabolique',
        'Insuffisance surrénalienne',
        'Hypercorticisme'
    ],
    'Neurologie': [
        'Migraine',
        'Épilepsie',
        'Accident vasculaire cérébral',
        'Sclérose en plaques',
        'Maladie de Parkinson',
        'Syndrome anxio-dépressif',
        'Névralgie',
        'Compression nerveuse',
        'Méningite',
        'Encéphalite'
    ],
    'Rhumatologie': [
        'Arthrose',
        'Polyarthrite rhumatoïde',
        'Spondylarthrite ankylosante',
        'Goutte',
        'Ostéoporose',
        'Fibromyalgie',
        'Lombalgie chronique',
        'Cervicalgie chronique',
        'Tendinite',
        'Syndrome du canal carpien'
    ],
    'Dermatologie': [
        'Eczéma',
        'Psoriasis',
        'Urticaire',
        'Dermite séborrhéique',
        'Acné',
        'Zona',
        'Herpès',
        'Mycose cutanée',
        'Gale',
        'Dermatite de contact'
    ],
    'Infectiologie': [
        'Infection bactérienne',
        'Infection virale',
        'Infection parasitaire',
        'Infection fongique',
        'Septicémie',
        'Grippe',
        'COVID-19',
        'Mononucléose infectieuse',
        'Paludisme',
        'Infection urinaire'
    ]
}

def require_doctor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_doctor:
            flash('Accès réservé aux médecins', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    developer_info = {
        'name': 'Dr. Bouchene Mohammed Mehdi',
        'email': 'bouchenemehdi@yahoo.com'
    }
    return render_template('login.html', developer_info=developer_info)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.name
        flash(f'Bienvenue {user.name} !', 'success')
        return redirect(url_for('dashboard'))
    
    flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
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
    
    try:
        date_filter = request.args.get('date_filter', 'today')
        specific_date = request.args.get('specific_date')
        search_query = request.args.get('search', '').strip()
        
        today = datetime.now().date()
        error_message = None
        
        # Base query avec jointures
        base_query = Appointment.query.outerjoin(
            Patient, Appointment.patient_id == Patient.id
        ).outerjoin(
            TemporaryPatient, Appointment.temp_patient_id == TemporaryPatient.id
        )

        # Appliquer le filtre de recherche si présent
        if search_query:
            base_query = base_query.filter(
                db.or_(
                    Patient.first_name.ilike(f'%{search_query}%'),
                    Patient.last_name.ilike(f'%{search_query}%'),
                    TemporaryPatient.first_name.ilike(f'%{search_query}%'),
                    TemporaryPatient.last_name.ilike(f'%{search_query}%')
                )
            )

        # Appliquer les filtres de date
        if date_filter == 'today':
            filter_date = today
            date_display = "d'aujourd'hui"
            appointments = base_query.filter(
                func.date(Appointment.date) == filter_date
            )
        elif date_filter == 'tomorrow':
            filter_date = today + timedelta(days=1)
            date_display = "de demain"
            appointments = base_query.filter(
                func.date(Appointment.date) == filter_date
            )
        elif date_filter == 'upcoming':
            date_display = "à venir"
            appointments = base_query.filter(
                Appointment.date >= today,
                Appointment.status == 'scheduled'
            )
        elif specific_date:
            try:
                filter_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
                date_display = f"du {filter_date.strftime('%d/%m/%Y')}"
                appointments = base_query.filter(
                    func.date(Appointment.date) == filter_date
                )
            except ValueError:
                error_message = "Format de date invalide"
                filter_date = today
                date_display = "d'aujourd'hui"
                appointments = base_query.filter(
                    func.date(Appointment.date) == filter_date
                )
        else:
            filter_date = today
            date_display = "d'aujourd'hui"
            appointments = base_query.filter(
                func.date(Appointment.date) == filter_date
            )

        # Finaliser la requête
        appointments = appointments.order_by(Appointment.date).all()

        return render_template('dashboard.html',
                            appointments=appointments,
                            date_display=date_display,
                            date_filter=date_filter,
                            error_message=error_message,
                            selected_date=getattr(filter_date, 'strftime', lambda x: '')('%Y-%m-%d') if specific_date or date_filter != 'upcoming' else '')

    except Exception as e:
        print(f"Erreur dans dashboard: {str(e)}")  # Log l'erreur
        flash("Une erreur s'est produite lors du chargement du tableau de bord", 'danger')
        return redirect(url_for('index'))

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
    
    # Ajouter la date d'aujourd'hui pour le calcul de l'âge
    today = datetime.now().date()
    
    return render_template('patients.html', 
                         patients=all_patients,
                         today=today)

@app.route('/patient/<int:patient_id>')
@require_doctor
def patient_details(patient_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.date.desc()).all()
    
    # Get next scheduled appointment
    next_appointment = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.date > datetime.now(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.date.asc()).first()
    
    today = datetime.now().date()
    
    return render_template('patient_details.html', 
                         patient=patient, 
                         appointments=appointments, 
                         next_appointment=next_appointment,
                         today=today)

@app.route('/patient/add', methods=['GET', 'POST'])
@require_doctor
def add_patient():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Validation de la date de naissance
            dob_str = request.form.get('date_of_birth')
            if not dob_str:
                raise ValueError("La date de naissance est obligatoire")
            
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if dob > today:
                raise ValueError("La date de naissance ne peut pas être dans le futur")

            # Validation des champs requis
            if not request.form.get('first_name'):
                raise ValueError("Le prénom est obligatoire")
            if not request.form.get('last_name'):
                raise ValueError("Le nom est obligatoire")

            # Get selected symptoms and diagnostics
            selected_symptoms = request.form.getlist('symptoms')
            other_symptoms = request.form.get('other_symptoms')
            symptoms_text = ', '.join(filter(None, selected_symptoms + [other_symptoms]))

            selected_diagnostics = request.form.getlist('diagnostics')
            other_diagnostic = request.form.get('other_diagnostic')
            diagnostic_text = ', '.join(filter(None, selected_diagnostics + [other_diagnostic]))

            new_patient = Patient(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                date_of_birth=dob,
                phone=request.form.get('phone'),
                weight=float(request.form.get('weight')) if request.form.get('weight') else None,
                height=float(request.form.get('height')) if request.form.get('height') else None,
                medical_history=request.form.get('medical_history'),
                symptoms=symptoms_text,
                diagnostic=diagnostic_text,
                treatment=request.form.get('treatment')
            )
            
            db.session.add(new_patient)
            db.session.flush()  # Pour obtenir l'ID du patient

            # Créer un rendez-vous immédiat (aujourd'hui)
            today_appointment = Appointment(
                patient_id=new_patient.id,
                doctor_id=session['user_id'],
                date=datetime.now(),  # Date d'aujourd'hui
                reason="Première consultation",
                status='completed'  # Rendez-vous déjà complété
            )
            db.session.add(today_appointment)
            db.session.flush()

            # Créer la consultation associée
            consultation = Consultation(
                appointment_id=today_appointment.id,
                date=datetime.now(),
                consultation_order=1,
                symptoms=symptoms_text,
                diagnostic=diagnostic_text,
                treatment=request.form.get('treatment'),
                notes=request.form.get('notes')
            )
            db.session.add(consultation)
            db.session.flush()

            # Traiter les services sélectionnés
            selected_services = request.form.getlist('initial_services')
            if selected_services:
                services_data = []
                total_amount = 0

                for service_id in selected_services:
                    service = Service.query.get(service_id)
                    if service and service.is_active:
                        services_data.append({
                            'id': service.id,
                            'name': service.name,
                            'price': service.price
                        })
                        total_amount += service.price

                if services_data:
                    payment = Payment(
                        consultation_id=consultation.id,
                        amount=total_amount,
                        services=services_data,
                        paid=request.form.get('paid', False) == 'on',
                        date=datetime.now()
                    )
                    db.session.add(payment)

            # Si un prochain rendez-vous est programmé
            next_appointment_date = request.form.get('next_appointment_date')
            if next_appointment_date:
                next_date = datetime.strptime(next_appointment_date, '%Y-%m-%d')
                next_appointment = Appointment(
                    patient_id=new_patient.id,
                    doctor_id=session['user_id'],
                    date=next_date,
                    reason="Consultation de suivi",
                    status='scheduled'
                )
                db.session.add(next_appointment)

            db.session.commit()
            flash('Patient ajouté avec succès', 'success')
            return redirect(url_for('patient_details', patient_id=new_patient.id))
            
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            print(f"Erreur: {str(e)}")  # Pour le débogage
            flash('Une erreur est survenue lors de l\'ajout du patient', 'danger')
    
    services = Service.query.filter_by(is_active=True).all()
    return render_template('add_patient.html', 
                         today=datetime.now().date().isoformat(),
                         services=services,
                         symptomes=SYMPTOMES,
                         diagnostics=DIAGNOSTICS)

@app.route('/appointment/add', methods=['GET', 'POST'])
def add_appointment():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Créer un patient temporaire
            temp_patient = TemporaryPatient(
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date(),
                phone=request.form.get('phone', '')
            )
            db.session.add(temp_patient)
            db.session.flush()

            # Créer le rendez-vous
            appointment = Appointment(
                temp_patient_id=temp_patient.id,
                doctor_id=session['user_id'],
                date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                reason="Consultation de suivi",
                status='scheduled'
            )
            db.session.add(appointment)
            db.session.commit()

            flash('Rendez-vous ajouté avec succès', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la création du rendez-vous', 'danger')
            return redirect(url_for('add_appointment'))

    today = datetime.now().date()
    return render_template('add_appointment.html', today=today)

@app.route('/appointment/<int:appointment_id>/update', methods=['GET', 'POST'])
def update_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    services = Service.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        # Mise à jour du statut
        appointment.status = request.form.get('status')
        
        # Si le rendez-vous est terminé, créer une consultation
        if appointment.status == 'completed':
            # Déterminer l'ordre de la consultation
            previous_consultations = Consultation.query.filter(
                Consultation.appointment.has(patient_id=appointment.patient_id)
            ).count()
            
            consultation = Consultation(
                appointment_id=appointment.id,
                date=datetime.now(),  # Utiliser la date actuelle
                consultation_order=previous_consultations + 1,
                symptoms=request.form.get('symptoms'),
                diagnostic=request.form.get('diagnostic'),
                treatment=request.form.get('treatment'),
                notes=request.form.get('notes'),
                follow_up_needed=bool(request.form.get('follow_up_needed')),
                next_appointment_date=datetime.strptime(request.form.get('next_appointment_date'), '%Y-%m-%d').date() if request.form.get('next_appointment_date') else None
            )
            db.session.add(consultation)
            
            # Mettre à jour le diagnostic et traitement du patient
            appointment.patient.diagnostic = request.form.get('diagnostic')
            appointment.patient.treatment = request.form.get('treatment')
            
            # Créer automatiquement le prochain rendez-vous si nécessaire
            if consultation.follow_up_needed and consultation.next_appointment_date:
                next_appointment = Appointment(
                    patient_id=appointment.patient_id,
                    doctor_id=session['user_id'],
                    date=datetime.combine(consultation.next_appointment_date, datetime.min.time()),
                    reason='Suivi ' + appointment.reason,
                    status='scheduled'
                )
                db.session.add(next_appointment)
                db.session.flush()  # Pour obtenir l'ID du prochain rendez-vous

                # Ajouter les services sélectionnés pour le prochain rendez-vous
                selected_services = request.form.getlist('next_appointment_services[]')
                services_data = []
                total_amount = 0

                for service_id in selected_services:
                    service = Service.query.get(service_id)
                    if service and service.is_active:
                        services_data.append({
                            'id': service.id,
                            'name': service.name,
                            'price': service.price
                        })
                        total_amount += service.price

                if services_data:
                    next_payment = Payment(
                        consultation_id=next_appointment.id,
                        amount=total_amount,
                        services=services_data,
                        paid=False
                    )
                    db.session.add(next_payment)
        
        db.session.commit()
        flash('Rendez-vous mis à jour avec succès', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('update_appointment.html', 
                         appointment=appointment,
                         services=services,
                         reasons=APPOINTMENT_REASONS)

@app.route('/appointment/<int:appointment_id>/services', methods=['POST'])
@require_doctor
def add_consultation_services(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    try:
        # Vérifier si une consultation existe déjà
        consultation = appointment.consultation
        if not consultation:
            # Créer une nouvelle consultation
            consultation = Consultation(
                appointment_id=appointment.id,
                date=datetime.now(),
                consultation_order=1
            )
            db.session.add(consultation)
            db.session.flush()  # Pour obtenir l'ID

        # Récupérer les services sélectionnés
        selected_services = request.form.getlist('services[]')
        services_data = []
        total_amount = 0
        
        # Traiter les services sélectionnés
        for service_id in selected_services:
            service = Service.query.get(service_id)
            if service and service.is_active:
                services_data.append({
                    'id': service.id,
                    'name': service.name,
                    'price': service.price
                })
                total_amount += service.price

        # Créer le paiement
        if services_data:
            payment = Payment(
                consultation_id=consultation.id,
                amount=total_amount,
                services=services_data,
                paid=request.form.get('paid') == 'on',
                date=datetime.now()
            )
            db.session.add(payment)

        # Marquer le rendez-vous comme terminé
        appointment.status = 'completed'
        
        db.session.commit()
        flash('Services et paiement enregistrés avec succès', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'ajout des services: {str(e)}")
        flash("Une erreur s'est produite lors de l'enregistrement des services", 'danger')
    
    return redirect(url_for('update_appointment', appointment_id=appointment_id))

@app.route('/services/manage', methods=['GET', 'POST'])
@require_doctor
def manage_services():
    if request.method == 'POST':
        service = Service(
            name=request.form['name'],
            price=float(request.form['price'])
        )
        db.session.add(service)
        db.session.commit()
        flash('Service ajouté avec succès', 'success')
        return redirect(url_for('manage_services'))

    services = Service.query.all()
    return render_template('manage_services.html', services=services)

@app.route('/services/edit/<int:service_id>', methods=['GET', 'POST'])
@require_doctor
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    if request.method == 'POST':
        try:
            service.name = request.form['name']
            service.price = float(request.form['price'])
            db.session.commit()
            flash('Service modifié avec succès', 'success')
            return redirect(url_for('manage_services'))
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la modification du service', 'danger')
    return render_template('edit_service.html', service=service)

@app.route('/payment/add/<int:consultation_id>', methods=['POST'])
def add_payment(consultation_id):  # Ajout du paramètre consultation_id
    consultation = Consultation.query.get_or_404(consultation_id)
    selected_services = request.form.getlist('services')
    services_data = []
    total_amount = 0

    for service_id in selected_services:
        service = Service.query.get(service_id)
        if service:
            services_data.append({
                'id': service.id,
                'name': service.name,
                'price': service.price
            })
            total_amount += service.price

    payment = Payment(
        consultation_id=consultation_id,
        amount=total_amount,
        services=services_data,
        paid=request.form.get('paid', False)
    )
    
    if payment.paid:
        payment.payment_date = datetime.now()

    db.session.add(payment)
    db.session.commit()

    flash('Paiement enregistré avec succès', 'success')
    return redirect(url_for('consultation_details', consultation_id=consultation_id))

@app.route('/temporary_patient/<int:temp_id>/convert', methods=['POST'])
@require_doctor
def convert_to_patient(temp_id):
    temp_patient = TemporaryPatient.query.get_or_404(temp_id)
    
    # Créer un nouveau patient permanent
    new_patient = Patient(
        first_name=temp_patient.first_name,
        last_name=temp_patient.last_name,
        date_of_birth=temp_patient.date_of_birth,
        phone=temp_patient.phone
    )
    db.session.add(new_patient)
    db.session.flush()  # Pour obtenir l'ID du nouveau patient
    
    # Mettre à jour tous les rendez-vous associés
    appointments = Appointment.query.filter_by(temp_patient_id=temp_id).all()
    for appointment in appointments:
        appointment.patient_id = new_patient.id
        appointment.temp_patient_id = None
    
    # Supprimer le patient temporaire
    db.session.delete(temp_patient)
    db.session.commit()
    
    flash('Patient ajouté avec succès. Veuillez compléter les informations.', 'success')
    return redirect(url_for('edit_patient', patient_id=new_patient.id))

@app.route('/patient/<int:patient_id>/edit', methods=['GET', 'POST'])
@require_doctor
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Get the latest consultation for this patient
    latest_consultation = db.session.query(Consultation)\
        .join(Appointment)\
        .filter(Appointment.patient_id == patient_id)\
        .order_by(Consultation.date.desc())\
        .first()
    
    if request.method == 'POST':
        try:
            patient.first_name = request.form.get('first_name')
            patient.last_name = request.form.get('last_name')
            patient.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
            patient.phone = request.form.get('phone')
            patient.medical_history = request.form.get('medical_history')
            patient.weight = float(request.form.get('weight')) if request.form.get('weight') else None
            patient.height = float(request.form.get('height')) if request.form.get('height') else None
            
            # Update symptoms
            selected_symptoms = request.form.getlist('symptoms')
            other_symptoms = request.form.get('other_symptoms')
            symptoms_text = ', '.join(filter(None, selected_symptoms + [other_symptoms]))
            patient.symptoms = symptoms_text
            
            # Update diagnostic
            selected_diagnostics = request.form.getlist('diagnostics')
            other_diagnostic = request.form.get('other_diagnostic')
            diagnostic_text = ', '.join(filter(None, selected_diagnostics + [other_diagnostic]))
            patient.diagnostic = diagnostic_text
            
            patient.treatment = request.form.get('treatment')
            
            # Create new consultation if changes were made
            if latest_consultation and (symptoms_text != latest_consultation.symptoms or 
                                    diagnostic_text != latest_consultation.diagnostic or
                                    patient.treatment != latest_consultation.treatment):
                new_consultation = Consultation(
                    appointment_id=latest_consultation.appointment.id,
                    date=datetime.now(),
                    consultation_order=latest_consultation.consultation_order + 1,
                    symptoms=symptoms_text,
                    diagnostic=diagnostic_text,
                    treatment=patient.treatment
                )
                db.session.add(new_consultation)
            
            db.session.commit()
            flash('Informations du patient mises à jour avec succès', 'success')
            return redirect(url_for('patient_details', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating patient: {str(e)}")
            flash('Une erreur est survenue lors de la mise à jour', 'danger')
            return redirect(url_for('edit_patient', patient_id=patient_id))
    
    # For GET requests, prepare the symptoms list
    patient_symptoms = []
    if latest_consultation and latest_consultation.symptoms:
        patient_symptoms = [s.strip() for s in latest_consultation.symptoms.split(',')]
    elif patient.symptoms:
        patient_symptoms = [s.strip() for s in patient.symptoms.split(',')]
    
    return render_template('edit_patient.html',
                         patient=patient,
                         patient_symptoms=patient_symptoms,
                         latest_consultation=latest_consultation,
                         symptomes=SYMPTOMES,
                         diagnostics=DIAGNOSTICS)

@app.route('/billing', methods=['GET', 'POST'])
@require_doctor
def billing():
    try:
        # Get all payments with complete relationships
        payments = db.session.query(Payment)\
            .join(Consultation)\
            .join(Appointment)\
            .join(Patient)\
            .filter(Payment.services.isnot(None))\
            .order_by(Payment.date.desc())\
            .all()

        # Statistics logic
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Default period (current month)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            start_date = today.replace(day=1)
            end_date = today

        total_patients = Patient.query.count()
        consultations_today = Consultation.query.filter(
            func.date(Consultation.date) == today
        ).count()
        consultations_this_week = Consultation.query.filter(
            func.date(Consultation.date) >= start_of_week,
            func.date(Consultation.date) <= end_of_week
        ).count()
        consultations_in_period = Consultation.query.filter(
            func.date(Consultation.date) >= start_date,
            func.date(Consultation.date) <= end_date
        ).count()
        revenue_in_period = db.session.query(func.sum(Payment.amount))\
            .filter(
                Payment.paid == True,
                func.date(Payment.date) >= start_date,
                func.date(Payment.date) <= end_date
            ).scalar() or 0

        return render_template('billing.html', 
                               payments=payments,
                               total_patients=total_patients,
                               consultations_today=consultations_today,
                               consultations_this_week=consultations_this_week,
                               consultations_in_period=consultations_in_period,
                               revenue_in_period=revenue_in_period,
                               start_date=start_date,
                               end_date=end_date)
    except Exception as e:
        print(f"Erreur dans la page de facturation: {str(e)}")
        flash("Une erreur s'est produite lors du chargement des factures", 'danger')
        return redirect(url_for('dashboard'))

@app.route('/payment/<int:payment_id>/mark-paid', methods=['POST'])
@require_doctor
def mark_payment_paid(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.paid = True
    payment.payment_date = datetime.now()
    db.session.commit()
    return {'success': True}

@app.route('/profile', methods=['GET', 'POST'])
@require_doctor
def profile():
    user = User.query.get(session['user_id'])
    settings = AppSettings.get_settings()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            # Update user credentials and name
            if request.form.get('new_password'):
                if check_password_hash(user.password, request.form.get('current_password')):
                    user.password = generate_password_hash(request.form.get('new_password'))
                    user.username = request.form.get('username')
                    user.name = request.form.get('name')  # Update name
                    user.speciality = request.form.get('speciality')  # Ajout de la spécialité
                    session['user_name'] = user.name  # Update session
                    session['user_speciality'] = user.speciality  # Ajout dans la session
                    flash('Informations de connexion mises à jour', 'success')
                else:
                    flash('Mot de passe actuel incorrect', 'danger')
            else:
                # Update just name and username without password change
                user.username = request.form.get('username')
                user.name = request.form.get('name')
                user.speciality = request.form.get('speciality')  # Ajout de la spécialité
                session['user_name'] = user.name  # Update session
                session['user_speciality'] = user.speciality  # Ajout dans la session
                flash('Informations mises à jour', 'success')
        
        elif action == 'update_settings':
            # Update app settings
            settings.app_name = request.form.get('app_name')
            settings.primary_color = request.form.get('primary_color')
            settings.last_updated = datetime.utcnow()
            
            # Traitement de l'image d'en-tête
            header_image = request.files.get('header_image')
            if header_image:
                settings.header_image = header_image.read()
                settings.header_image_type = header_image.content_type

            # Traitement de l'image du cachet
            stamp_image = request.files.get('stamp_image')
            if stamp_image:
                settings.stamp_image = stamp_image.read()
                settings.stamp_image_type = stamp_image.content_type

            # Mise à jour du texte du pied de page
            settings.footer_text = request.form.get('footer_text')
            
            flash('Paramètres de l\'application mis à jour', 'success')
            
        db.session.commit()
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=user, settings=settings)

@app.route('/patient/<int:patient_id>/sick-leave', methods=['POST'])
@require_doctor
def generate_sick_leave(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = User.query.get(session['user_id'])
    settings = AppSettings.get_settings()
    
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
    reason = request.form.get('reason')
    
    """
    ...existing code...
    """

@app.route('/preview/sick-leave/<int:patient_id>', methods=['POST'])
@require_doctor
def preview_sick_leave(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = User.query.get(session['user_id'])
    settings = AppSettings.get_settings()
    
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
    reason = request.form.get('reason')
    
    return render_template('sick_leave.html',
                         patient=patient,
                         doctor=doctor,
                         app_settings=settings,
                         start_date=start_date,
                         end_date=end_date,
                         reason=reason,
                         today=datetime.now())

@app.route('/preview/chronic-disease/<int:patient_id>', methods=['POST'])
@require_doctor
def preview_chronic_disease(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = User.query.get(session['user_id'])
    settings = AppSettings.get_settings()
    
    disease = request.form['disease']
    disease_start = datetime.strptime(request.form['disease_start'], '%Y-%m-%d')
    notes = request.form.get('notes')
    
    return render_template('chronic_disease.html',
                         patient=patient,
                         doctor=doctor,
                         app_settings=settings,
                         disease=disease,
                         disease_start=disease_start,
                         notes=notes,
                         today=datetime.now())

@app.route('/patient/<int:patient_id>/chronic-disease', methods=['POST'])
@require_doctor
def generate_chronic_disease(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = User.query.get(session['user_id'])
    settings = AppSettings.get_settings()
    
    disease = request.form['disease']
    disease_start = datetime.strptime(request.form['disease_start'], '%Y-%m-%d')
    notes = request.form.get('notes')
    
    """
    ...existing code...
    """

@app.route('/export/consultations')
@require_doctor
def export_consultations():
    consultations = Consultation.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Patient', 'Diagnostic', 'Traitement'])
    
    for consultation in consultations:
        writer.writerow([
            consultation.date,
            f"{consultation.appointment.patient.first_name} {consultation.appointment.patient.last_name}",
            consultation.diagnostic,
            consultation.treatment
        ])
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=consultations.csv'}
    )

@app.route('/statistics')
@require_doctor
def statistics():
    current_month = datetime.now().month
    total_patients = Patient.query.count()
    monthly_consultations = Consultation.query.filter(
        func.extract('month', Consultation.date) == current_month
    ).count()
    revenue = db.session.query(func.sum(Payment.amount))\
        .filter(Payment.paid == True).scalar() or 0
    
    return render_template('statistics.html',
                         total_patients=total_patients,
                         monthly_consultations=monthly_consultations,
                         revenue=revenue)

# Initialize the database
with app.app_context():
    try:
        db.drop_all()
        db.create_all()
        
        # Créer le compte médecin par défaut
        if not User.query.filter_by(role='doctor').first():
            doctor = User(
                username='doctor',
                password=generate_password_hash('doctor123'),
                name='',  # Empty name to force setting on first login
                role='doctor'
            )
            db.session.add(doctor)
        
        # Créer le compte assistant par défaut
        if not User.query.filter_by(role='assistant').first():
            assistant = User(
                username='assistant',
                password=generate_password_hash('assistant123'),
                name='Assistant',
                role='assistant'
            )
            db.session.add(assistant)
            
        db.session.commit()
            
    except Exception as e:
        print(f"Error during database initialization: {e}")

app.register_blueprint(services_bp, url_prefix='/services')

if __name__ == '__main__':
    app.run(debug=True)