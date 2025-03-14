from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import Service, db

services_bp = Blueprint('services', __name__)

@services_bp.route('/services')
def services():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))
    
    all_services = Service.query.all()
    return render_template('services.html', services=all_services)

@services_bp.route('/service/add', methods=['GET', 'POST'])
def add_service():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        
        new_service = Service(name=name, price=price)
        db.session.add(new_service)
        db.session.commit()
        
        flash('Service added successfully', 'success')
        return redirect(url_for('services.services'))
    
    return render_template('add_service.html')

@services_bp.route('/service/<int:service_id>/update', methods=['GET', 'POST'])
def update_service(service_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))
    
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'POST':
        service.name = request.form.get('name')
        service.price = request.form.get('price')
        db.session.commit()
        
        flash('Service updated successfully', 'success')
        return redirect(url_for('services.services'))
    
    return render_template('update_service.html', service=service)
