from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  # Ajout de l'import manquant

db = SQLAlchemy()

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)

class Patient(db.Model):
    __tablename__ = 'patient'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    medical_history = db.Column(db.Text)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    first_consultation_diagnostic = db.Column(db.Text)
    first_consultation_treatment = db.Column(db.Text)
    first_consultation_notes = db.Column(db.Text)
    
    # Ajout des index
    __table_args__ = (
        db.Index('idx_patient_last_name', 'last_name'),
        db.Index('idx_patient_first_name', 'first_name'),
    )

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), nullable=False, default='Clinique Médicale')
    logo_url = db.Column(db.String(200))
    clinic_address = db.Column(db.Text)  # Ajout de l'adresse
    primary_color = db.Column(db.String(20), default='#0d6efd')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    header_image = db.Column(db.LargeBinary)  # Image d'en-tête
    header_image_type = db.Column(db.String(32))  # Type MIME de l'image
    footer_text = db.Column(db.Text)  # Texte du pied de page
    stamp_image = db.Column(db.LargeBinary)  # Image du cachet
    stamp_image_type = db.Column(db.String(32))  # Type MIME du cachet

class MedicalDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    type = db.Column(db.String(50))  # 'xray', 'blood_test', 'scan'
    file_name = db.Column(db.String(200))
    file_path = db.Column(db.String(500))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    medication_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(50))
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Notification system without external services
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100))
    message = db.Column(db.Text)
    type = db.Column(db.String(20))  # 'appointment', 'system'
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)