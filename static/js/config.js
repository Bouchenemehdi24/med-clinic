const CONFIG = {
    ANIMATION_DURATION: 300,
    DATE_FORMAT: 'DD/MM/YYYY',
    TIME_FORMAT: 'HH:mm',
    API_ENDPOINTS: {
        APPOINTMENTS: '/api/appointments',
        PATIENTS: '/api/patients',
        SERVICES: '/api/services'
    },
    ALERT_TIMEOUT: 5000,
    CALENDAR: {
        firstDay: 1,
        minTime: '08:00:00',
        maxTime: '18:00:00',
        slotDuration: '00:15:00'
    }
};

export default CONFIG;
