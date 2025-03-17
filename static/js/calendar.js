document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        slotMinTime: '08:00:00',
        slotMaxTime: '18:00:00',
        events: '/api/appointments',
        editable: true,
        eventDrop: function(info) {
            updateAppointment(info.event);
        }
    });
    calendar.render();
});
