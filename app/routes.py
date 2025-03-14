@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        # Créer le patient
        patient = Patient(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d'),
            phone=request.form['phone'],
            email=request.form['email'],
            address=request.form['address'],
            weight=float(request.form['weight']) if request.form['weight'] else None,
            height=float(request.form['height']) if request.form['height'] else None,
            medical_history=request.form['medical_history']
        )
        db.session.add(patient)
        db.session.flush()  # Pour obtenir l'ID du patient

        # Créer la première consultation
        consultation = Consultation(
            patient_id=patient.id,
            date=datetime.now(),
            diagnostic=request.form['diagnostic'],
            treatment=request.form['treatment'],
            notes=request.form['consultation_notes']
        )
        db.session.add(consultation)
        
        db.session.commit()
        flash('Patient ajouté avec succès avec sa première consultation', 'success')
        return redirect(url_for('patient_detail', patient_id=patient.id))

    return render_template('add_patient.html')
