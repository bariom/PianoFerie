from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from calendar import monthrange, day_name, Calendar
from datetime import date, timedelta, datetime
from config import Config
from extensions import db, migrate

# Configurazione Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inizializza database e migrazioni
db.init_app(app)
migrate.init_app(app, db)

# Inizializza Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Devi effettuare il login per accedere."
login_manager.login_message_category = "warning"

# Modelli
from models import User, Holiday, Booking


# Caricamento utente per Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Route Homepage
@app.route('/')
def index():
    return render_template('index.html')


# Route Registrazione
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([name, email, password, confirm_password]):
            flash('Tutti i campi sono obbligatori.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Le password non corrispondono.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registrazione completata! Ora puoi accedere.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Route Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login effettuato con successo!', 'success')
            return redirect(url_for('admin_dashboard') if user.is_admin else url_for('dashboard'))
        else:
            flash('Email o password errati.', 'danger')

    return render_template('login.html')


# Route Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('login'))


# Route Dashboard Utente
@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user

    # Ottieni tutte le prenotazioni dell'utente
    bookings = Booking.query.filter_by(user_id=user.id).all()

    # Prepara i dati per le prenotazioni
    booked_holidays = [
        {
            'id': booking.id,
            'date': Holiday.query.get(booking.holiday_id).date.strftime('%Y-%m-%d'),
            'cost': Holiday.query.get(booking.holiday_id).cost,
            'is_validated': booking.is_validated
        }
        for booking in bookings
    ]

    # Ottieni l'orario corrente per costruire l'URL
    now = datetime.now()

    # Renderizza il template con i dati aggiornati
    return render_template(
        'dashboard.html',
        user=user,
        booked_holidays=booked_holidays,
        now=now
    )







# Route Dashboard Amministratore
@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for('dashboard'))

    now = datetime.now()
    return render_template('admin_dashboard.html', now=now)


# Route Calendario Dipendente
@app.route('/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def employee_calendar_view(year, month):
    user = current_user  # Usa l'utente loggato direttamente
    cal = Calendar(firstweekday=0)  # Inizia con lunedì
    month_days = cal.monthdayscalendar(year, month)  # Elenco delle settimane con i giorni

    # Ottieni il primo e l'ultimo giorno del mese
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Ottieni le ferie dal database per il mese selezionato
    holidays = Holiday.query.filter(Holiday.date.between(first_day, last_day)).all()
    holiday_data = {holiday.date: holiday for holiday in holidays}

    # Costruisci i dati del calendario
    calendar_data = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:  # Giorno vuoto nel calendario
                week_data.append({'date': None, 'cost': None, 'is_booked': False})
            else:
                current_date = date(year, month, day)
                holiday = holiday_data.get(current_date)
                if holiday:
                    cost = holiday.cost
                    holiday_id = holiday.id
                else:
                    cost = 10  # Costo di default
                    holiday_id = None

                week_data.append({
                    'date': current_date,
                    'cost': cost,
                    'is_booked': Booking.query.filter_by(user_id=user.id, holiday_id=holiday_id).first() is not None
                })
        calendar_data.append(week_data)

    # Gestione della prenotazione
    warnings = []
    if request.method == 'POST':
        selected_dates = request.form.getlist('selected_dates')
        if not selected_dates:
            warnings.append('Seleziona almeno un giorno per prenotare.')
            return render_template('employee_calendar.html', calendar_data=calendar_data, year=year, month=month, warnings=warnings)

        total_cost = 0
        required_days = len(selected_dates)
        new_bookings = []

        for date_str in selected_dates:
            holiday_date = date.fromisoformat(date_str)
            holiday = holiday_data.get(holiday_date)
            if not holiday:
                warnings.append(f"Nessuna festività trovata per la data {holiday_date}.")
                return render_template('employee_calendar.html', calendar_data=calendar_data, year=year, month=month, warnings=warnings)

            total_cost += holiday.cost
            new_bookings.append(holiday)

        # Verifica crediti
        if total_cost > user.credits:
            warnings.append(f"Crediti insufficienti. Hai {user.credits} crediti disponibili, ma ne servono {total_cost}.")
        # Verifica giorni di ferie residui
        if required_days > user.remaining_holiday_days:
            warnings.append(f"Giorni di ferie residui insufficienti. Hai {user.remaining_holiday_days} giorni, ma ne servono {required_days}.")

        # Se ci sono warning, interrompi la prenotazione
        if warnings:
            return render_template('employee_calendar.html', calendar_data=calendar_data, year=year, month=month, warnings=warnings)

        # Aggiorna crediti e giorni residui
        user.credits -= total_cost
        user.remaining_holiday_days -= required_days

        for holiday in new_bookings:
            booking = Booking(user_id=user.id, holiday_id=holiday.id)
            db.session.add(booking)

        db.session.commit()
        flash('Ferie prenotate con successo!', 'success')
        return redirect(url_for('employee_calendar_view', year=year, month=month))

    return render_template('employee_calendar.html', calendar_data=calendar_data, year=year, month=month, warnings=warnings)

# Route Calendario Amministratore
@app.route('/admin/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def admin_calendar(year, month):
    # Verifica che l'utente sia amministratore
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Accesso negato. Solo gli amministratori possono accedere a questa pagina.', 'danger')
        return redirect(url_for('dashboard'))

    # Ottieni il primo e l'ultimo giorno del mese
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Ottieni le giornate con costi specifici
    holidays = Holiday.query.filter(Holiday.date.between(first_day, last_day)).all()
    holiday_data = {holiday.date: holiday.cost for holiday in holidays}

    # Costruisci il calendario
    days_in_month = monthrange(year, month)[1]
    calendar_days = [
        {
            'date': first_day + timedelta(days=i),
            'day_name': day_name[(first_day + timedelta(days=i)).weekday()],  # Nome del giorno
            'cost': holiday_data.get(first_day + timedelta(days=i), 0 if (first_day + timedelta(days=i)).weekday() >= 5 else Config.DEFAULT_COST)
        }
        for i in range(days_in_month)
    ]

    # Aggiornamento costi
    if request.method == 'POST':
        updated_costs = request.form.to_dict()
        for day, cost in updated_costs.items():
            if cost.isdigit():
                day_date = date.fromisoformat(day)
                holiday = Holiday.query.filter_by(date=day_date).first()

                # Aggiorna il costo o crea un nuovo record
                if holiday:
                    holiday.cost = int(cost)
                else:
                    new_holiday = Holiday(date=day_date, cost=int(cost))
                    db.session.add(new_holiday)
        db.session.commit()
        flash('Costi aggiornati con successo!', 'success')
        return redirect(url_for('admin_calendar', year=year, month=month))

    return render_template('admin_calendar.html', calendar_days=calendar_days, year=year, month=month)


@app.route('/all-bookings-calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def all_bookings_calendar(year, month):
    from calendar import Calendar

    # Verifica che l'utente sia amministratore
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for('dashboard'))

    cal = Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Ottieni utenti selezionati (via POST o mostra tutti di default)
    selected_users = request.form.getlist('selected_users') if request.method == 'POST' else []
    if not selected_users:
        all_users = User.query.all()
        selected_users = [str(user.id) for user in all_users]

    # Ottieni prenotazioni in base agli utenti selezionati
    bookings = Booking.query.join(User).join(Holiday).filter(
        Booking.user_id.in_(selected_users),
        Holiday.date.between(first_day, last_day)
    ).all()

    # Organizza le prenotazioni per data
    bookings_by_date = {}
    for booking in bookings:
        holiday = Holiday.query.get(booking.holiday_id)
        if holiday.date not in bookings_by_date:
            bookings_by_date[holiday.date] = []
        bookings_by_date[holiday.date].append(booking.user_id)

    # Costruisci i dati del calendario
    calendar_data = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'date': None, 'bookings': []})
            else:
                current_date = date(year, month, day)
                bookings = bookings_by_date.get(current_date, [])
                week_data.append({'date': current_date, 'bookings': bookings})
        calendar_data.append(week_data)

    # Ottieni tutti gli utenti per i filtri
    all_users = User.query.all()

    return render_template(
        'all_bookings_calendar.html',
        calendar_data=calendar_data,
        all_users=all_users,
        selected_users=[int(uid) for uid in selected_users],
        year=year,
        month=month
    )


@app.route('/cancel-booking', methods=['POST'])
@login_required
def cancel_booking():
    booking_id = request.form.get('booking_id')

    if not booking_id:
        flash("ID prenotazione non valido.", "danger")
        return redirect(url_for('dashboard'))

    booking = Booking.query.get(booking_id)

    # Verifica che il booking appartenga all'utente corrente
    if not booking or booking.user_id != current_user.id:
        flash("Prenotazione non trovata o non autorizzata.", "danger")
        return redirect(url_for('dashboard'))

    # Ottieni l'utente e il giorno di ferie associati
    user = User.query.get(current_user.id)
    holiday = Holiday.query.get(booking.holiday_id)

    if holiday:
        # Restituisci i crediti e i giorni ferie
        user.credits += holiday.cost
        user.remaining_holiday_days += 1

        # Rimuovi la prenotazione
        db.session.delete(booking)
        db.session.commit()

        flash("Prenotazione annullata con successo. Crediti e giorni ferie aggiornati.", "success")
    else:
        flash("Errore durante l'annullamento della prenotazione.", "danger")

    return redirect(url_for('dashboard'))





@app.route('/validate-bookings', methods=['GET', 'POST'])
@login_required
def validate_bookings():
    if not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for('dashboard'))

    # Ottenere tutte le prenotazioni non validate
    bookings = Booking.query.filter_by(is_validated=False).all()

    # Prepara i dati per il template
    booking_data = [
        {
            'id': booking.id,
            'user_name': User.query.get(booking.user_id).name,  # Ottieni il nome dell'utente
            'holiday_date': Holiday.query.get(booking.holiday_id).date.strftime('%Y-%m-%d'),
            'holiday_cost': Holiday.query.get(booking.holiday_id).cost
        }
        for booking in bookings
    ]

    if request.method == 'POST':
        validated_bookings = request.form.getlist('validate')
        for booking_id in validated_bookings:
            booking = Booking.query.get(booking_id)
            if booking:
                booking.is_validated = True
                db.session.commit()

        flash("Prenotazioni validate con successo!", "success")
        return redirect(url_for('validate_bookings'))

    return render_template('validate_bookings.html', bookings=booking_data)


# Avvio dell'applicazione
if __name__ == '__main__':
    app.run(debug=True)
