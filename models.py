from flask_sqlalchemy import SQLAlchemy

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