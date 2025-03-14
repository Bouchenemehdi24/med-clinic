from flask import request, current_app
from sqlalchemy.orm import joinedload

@app.route('/patient/')
def list_patients():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    patients = Patient.query\
        .options(joinedload('appointments'))\
        .order_by(Patient.last_name)\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('patient_list.html', patients=patients)
