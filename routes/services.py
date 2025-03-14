from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps

services_bp = Blueprint('services', __name__)

def require_doctor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_role') != 'doctor':
            flash('Accès réservé aux médecins', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@services_bp.route('/manage', methods=['GET', 'POST'])
@require_doctor
def manage_services():
    from app import Service, db  # Import local pour éviter les imports circulaires
    
    if request.method == 'POST':
        service = Service(
            name=request.form['name'],
            price=float(request.form['price'])
        )
        db.session.add(service)
        db.session.commit()
        flash('Service ajouté avec succès', 'success')
        return redirect(url_for('services.manage_services'))

    services = Service.query.all()
    return render_template('manage_services.html', services=services)

@services_bp.route('/update-service', methods=['POST'])
@require_doctor
def update_service_endpoint():
    from app import Service, db
    
    data = request.get_json()
    service = Service.query.get(data['id'])
    if service:
        service.name = data['name']
        service.price = float(data['price'])
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404
