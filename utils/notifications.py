def send_appointment_reminder(appointment):
    if appointment.patient.phone:
        message = f"Rappel: RDV le {appointment.date.strftime('%d/%m/%Y')} à {appointment.date.strftime('%H:%M')}"
        send_sms(appointment.patient.phone, message)
    
    if appointment.patient.email:
        send_email(
            to=appointment.patient.email,
            subject="Rappel de rendez-vous",
            template='email/appointment_reminder.html',
            appointment=appointment
        )
