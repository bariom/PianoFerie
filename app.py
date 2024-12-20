from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from calendar import monthrange, day_name, Calendar
from datetime import date, timedelta, datetime
from config import Config
from extensions import db, migrate
from sqlalchemy.orm import joinedload
import locale

# Configurazione Flask
app = Flask(__name__)
app.config.from_object(Config)

# Configura SQLAlchemy per ripristinare connessioni perse
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Controlla che la connessione sia attiva prima di riutilizzarla
    'pool_size': 5,         # Numero di connessioni nel pool
    'max_overflow': 10,     # Connessioni extra se il pool è pieno
    'pool_timeout': 30      # Timeout prima di dichiarare un errore
}

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

INACTIVITY_TIMEOUT = 5 * 60
@app.before_request
def check_inactivity():
    if current_user.is_authenticated:
        now = datetime.utcnow().timestamp()
        last_activity = session.get('last_activity')

        if last_activity is not None:
            elapsed = now - last_activity
            if elapsed > INACTIVITY_TIMEOUT:
                logout_user()
                flash("Sei stato scollegato per inattività.", "info")
                return redirect(url_for('login'))

        # Imposta o aggiorna l'ultimo timestamp di attività
        session['last_activity'] = now


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
            session['last_activity'] = datetime.utcnow().timestamp()
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
            'cost': Holiday.query.get(booking.holiday_id).cost / 2 if booking.is_half_day else Holiday.query.get(booking.holiday_id).cost,
            'session': (
                'Mattino' if booking.is_half_day and booking.session == 'morning' else
                'Pomeriggio' if booking.is_half_day and booking.session == 'afternoon' else
                'Intera giornata'
            ),
            'status': (
                'Rifiutata' if booking.is_rejected else
                'Validata' if booking.is_validated else
                'In attesa'
            ),
            'is_rejected': booking.is_rejected
        }
        for booking in bookings
    ]

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

    show_confirmation_modal = request.args.get('confirm', 'false') == 'true'
    show_process_year_end_modal = request.args.get('process_year_end') == 'true'
    now = datetime.now()

    return render_template(
        'admin_dashboard.html',
        now=now,
        show_confirmation_modal=show_confirmation_modal,
        show_process_year_end_modal = show_process_year_end_modal


    )


@app.route('/admin/users', methods=['GET'])
@login_required
def admin_users():
    if not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get(user_id)
    if not user:
        flash("Utente non trovato.", "danger")
        return redirect(url_for('admin_users'))

    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.credits = int(request.form.get('credits', user.credits))
        user.annual_holiday_days = float(request.form.get('annual_holiday_days', user.annual_holiday_days))
        user.remaining_holiday_days = float(request.form.get('remaining_holiday_days', user.remaining_holiday_days))
        user.annual_credits = int(request.form.get('annual_credits', user.annual_credits))

        # Se vuoi cambiare password, aggiungi un controllo
        new_password = request.form.get('password')
        if new_password:
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash("Dati utente aggiornati con successo!", "success")
        return redirect(url_for('admin_users'))

    return render_template('edit_user.html', user=user)


@app.route('/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def employee_calendar_view(year, month):
    user = current_user
    cal = Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    holidays = Holiday.query.filter(Holiday.date.between(first_day, last_day)).all()
    holiday_data = {holiday.date: holiday for holiday in holidays}

    calendar_data = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'date': None, 'cost': None, 'css_class': 'empty'})
            else:
                current_date = date(year, month, day)
                holiday = holiday_data.get(current_date)
                cost = holiday.cost if holiday else 10
                holiday_id = holiday.id if holiday else None

                is_weekend = current_date.weekday() >= 5  # Sabato o Domenica
                is_holiday = holiday and holiday.cost == 0

                css_class = (
                    'holiday' if is_holiday else
                    'weekend' if is_weekend else
                    ''
                )

                bookings = Booking.query.filter_by(user_id=user.id, holiday_id=holiday_id).all()

                full_day_booking = next(
                    (b for b in bookings if not b.is_half_day), None
                )
                half_day_bookings = [
                    {
                        'session': b.session,
                        'is_validated': b.is_validated,
                        'is_rejected': b.is_rejected
                    }
                    for b in bookings if b.is_half_day
                ]

                week_data.append({
                    'date': current_date,
                    'cost': cost,
                    'holiday_id': holiday_id,
                    'css_class': css_class,
                    'full_day_booking': full_day_booking,
                    'half_day_bookings': half_day_bookings,
                    'is_holiday': is_holiday,
                    'can_book': not is_holiday and not is_weekend
                })
        calendar_data.append(week_data)

    # Saldi aggiornati
    credits = user.credits
    remaining_days = user.remaining_holiday_days

    warnings = []
    if request.method == 'POST':
        selected_dates = request.form.getlist('selected_dates')
        new_bookings = []
        for date_str in selected_dates:
            holiday_date = date.fromisoformat(date_str)
            holiday = holiday_data.get(holiday_date)

            if not holiday:
                warnings.append(f"Nessuna festività trovata per la data {holiday_date}.")
                continue

            session = request.form.get(f'session_{holiday_date}')
            is_half_day = session in ['morning', 'afternoon']

            existing_full_booking = Booking.query.filter_by(
                user_id=user.id, holiday_id=holiday.id, is_half_day=False
            ).first()
            existing_half_day_booking = Booking.query.filter_by(
                user_id=user.id, holiday_id=holiday.id, is_half_day=True, session=session
            ).first()

            if is_half_day:
                if existing_full_booking:
                    warnings.append(f"Il giorno {holiday_date} è già prenotato come giornata intera.")
                    continue
                if existing_half_day_booking:
                    warnings.append(f"La sessione {session} del giorno {holiday_date} è già prenotata.")
                    continue
            else:
                if existing_full_booking or existing_half_day_booking:
                    warnings.append(f"Il giorno {holiday_date} ha già una prenotazione (mezza o intera giornata).")
                    continue

            new_booking = Booking(
                user_id=user.id,
                holiday_id=holiday.id,
                holiday=holiday,
                is_half_day=is_half_day,
                session=session if is_half_day else None
            )
            new_bookings.append(new_booking)

        total_cost = sum(
            booking.holiday.cost / 2 if booking.is_half_day else booking.holiday.cost
            for booking in new_bookings
        )
        required_days = sum(
            0.5 if booking.is_half_day else 1
            for booking in new_bookings
        )

        if total_cost > user.credits:
            warnings.append(f"Crediti insufficienti. Hai {user.credits} crediti disponibili.")
            return render_template('employee_calendar.html', calendar_data=calendar_data, year=year, month=month, warnings=warnings)

        if required_days > user.remaining_holiday_days:
            warnings.append(f"Giorni di ferie insufficienti. Hai {user.remaining_holiday_days} giorni disponibili.")
            return render_template('employee_calendar.html', calendar_data=calendar_data, year=year, month=month, warnings=warnings)

        user.credits -= total_cost
        user.remaining_holiday_days -= required_days
        db.session.add(user)

        for booking in new_bookings:
            db.session.add(booking)
        db.session.commit()

        flash('Ferie prenotate con successo!', 'success')
        return redirect(url_for('employee_calendar_view', year=year, month=month))

    # Nome del mese in italiano
    locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
    month_name = datetime(year, month, 1).strftime('%B')

    return render_template(
        'employee_calendar.html',
        calendar_data=calendar_data,
        year=year,
        month=month,
        warnings=warnings,
        month_name=month_name,
        credits=credits,
        remaining_days=remaining_days
    )



from babel.dates import format_date

# Route Calendario Amministratore
@app.route('/admin/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def admin_calendar(year, month):
    # Verifica che l'utente sia amministratore
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Accesso negato. Solo gli amministratori possono accedere a questa pagina.', 'danger')
        return redirect(url_for('dashboard'))

    # Nome del mese in italiano
    month_name = format_date(date(year, month, 1), "MMMM", locale="it_IT")

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
            'day_name': format_date(first_day + timedelta(days=i), "EEEE", locale="it_IT"),  # Nome del giorno
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

    return render_template('admin_calendar.html', calendar_days=calendar_days, year=year, month=month, month_name=month_name)

@app.route('/all-bookings-calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def all_bookings_calendar(year, month):
    from calendar import Calendar

    # Verifica che l'utente sia amministratore
    if not current_user.is_authenticated:    # commentato: or not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for('dashboard'))

    cal = Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    # Imposta il locale in italiano
    locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

    # Nome del mese
    month_name = datetime(year, month, 1).strftime('%B')

    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Ottieni gli utenti selezionati
    selected_users = request.form.getlist('selected_users') if request.method == 'POST' else []
    if not selected_users:
        all_users = User.query.all()
        selected_users = [str(user.id) for user in all_users]

    # Ottieni tutte le festività e i loro costi
    holidays = Holiday.query.filter(Holiday.date.between(first_day, last_day)).all()
    holiday_dates = {holiday.date: holiday.cost for holiday in holidays}

    # Ottieni prenotazioni in base agli utenti selezionati
    bookings = Booking.query.join(User).join(Holiday).filter(
        Booking.user_id.in_(selected_users),
        Holiday.date.between(first_day, last_day)
    ).options(joinedload(Booking.holiday), joinedload(Booking.user)).all()

    # Organizza le prenotazioni per data
    bookings_by_date = {}
    for booking in bookings:
        holiday = booking.holiday
        user = booking.user

        if holiday.date not in bookings_by_date:
            bookings_by_date[holiday.date] = []

        bookings_by_date[holiday.date].append({
            'id': booking.id,
            'user_name': user.name,
            'is_half_day': booking.is_half_day,
            'session': booking.session,
            'is_validated': booking.is_validated,
            'is_rejected': booking.is_rejected
        })

    # Costruisci i dati del calendario
    calendar_data = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'date': None, 'bookings': [], 'is_holiday': False, 'cost': None})
            else:
                current_date = date(year, month, day)
                cost = holiday_dates.get(current_date, 10)  # Assumi un costo di default se non esiste nel DB
                is_holiday = cost == 0  # Festivo se il costo è zero
                week_data.append({
                    'date': current_date,
                    'bookings': bookings_by_date.get(current_date, []),
                    'is_holiday': is_holiday,
                    'cost': cost
                })
        calendar_data.append(week_data)

    # Ottieni tutti gli utenti per i filtri
    all_users = User.query.all()

    return render_template(
        'all_bookings_calendar.html',
        calendar_data=calendar_data,
        all_users=all_users,
        selected_users=[int(uid) for uid in selected_users],
        year=year,
        month=month,
        month_name=month_name
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
        # Calcola il rimborso in base al tipo di prenotazione
        if booking.is_half_day:
            user.credits += holiday.cost // 2  # Aggiungi metà del costo
            user.remaining_holiday_days += 0.5  # Aggiungi mezza giornata
        else:
            user.credits += holiday.cost  # Aggiungi l'intero costo
            user.remaining_holiday_days += 1  # Aggiungi una giornata intera

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

    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        action = request.form.get('action')
        next_page = request.form.get('next', None)

        booking = Booking.query.get(booking_id)
        if not booking:
            flash("Prenotazione non trovata.", "danger")
            return redirect(url_for('validate_bookings'))

        if action == "validate":
            booking.is_validated = True
            db.session.add(booking)
            flash("Prenotazione validata con successo.", "success")

        elif action == "reject":
            # Ripristina il saldo ferie e crediti
            user = booking.user
            holiday = booking.holiday

            if booking.is_half_day:
                user.credits += holiday.cost / 2
                user.remaining_holiday_days += 0.5
            else:
                user.credits += holiday.cost
                user.remaining_holiday_days += 1

            booking.is_rejected = True
            db.session.add(user)
            db.session.add(booking)
            flash("Prenotazione rifiutata con successo.", "success")

        db.session.commit()

        # Se `next_page` è presente, redirigi lì, altrimenti vai alla pagina di default
        if next_page:
            return redirect(next_page)
        else:
            return redirect(url_for('validate_bookings'))

    # GET request: Applichiamo la paginazione
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination = Booking.query \
        .options(joinedload(Booking.user), joinedload(Booking.holiday)) \
        .filter_by(is_validated=False, is_rejected=False) \
        .paginate(page=page, per_page=per_page, error_out=False)

    # Ottieni i bookings della pagina corrente
    bookings = pagination.items

    # Prepara i dati per il template senza query aggiuntive
    booking_data = [
        {
            'id': booking.id,
            'user_name': booking.user.name,
            'holiday_date': booking.holiday.date.strftime('%Y-%m-%d'),
            'holiday_cost': booking.is_half_day and booking.holiday.cost / 2 or booking.holiday.cost,
            'is_half_day': booking.is_half_day,
            'session': (
                'Mattino' if booking.is_half_day and booking.session == 'morning' else
                'Pomeriggio' if booking.is_half_day and booking.session == 'afternoon' else
                'Intera giornata'
            )
        }
        for booking in bookings
    ]

    return render_template(
        'validate_bookings.html',
        bookings=booking_data,
        pagination=pagination
    )



@app.route('/delete-rejected-bookings', methods=['POST'])
@login_required
def delete_rejected_bookings():
    if not current_user.is_admin:
        flash("Accesso non autorizzato. Solo gli amministratori possono eseguire questa operazione.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Logica per eliminare le prenotazioni rifiutate
    rejected_bookings = Booking.query.filter_by(is_rejected=True).all()

    if not rejected_bookings:
        flash("Non ci sono prenotazioni rifiutate da eliminare.", "info")
    else:
        count = len(rejected_bookings)
        for booking in rejected_bookings:
            db.session.delete(booking)
        db.session.commit()
        flash(f"Sono state eliminate {count} prenotazioni rifiutate.", "success")

    return redirect(url_for('admin_dashboard'))


@app.route('/help')
@login_required
def help_page():
    # Verifica che l'utente sia amministratore
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Accesso negato. Solo gli amministratori possono accedere a questa pagina.", "danger")
        return redirect(url_for('dashboard'))

    return render_template('help.html')


@app.route('/admin/process_year_end', methods=['POST'])
def process_year_end():
    try:
        # Aggiorna i saldi per tutti gli utenti non admin
        users = User.query.filter_by(is_admin=False).all()
        for user in users:
            user.remaining_holiday_days += user.annual_holiday_days
            user.credits += user.annual_credits

        # Salva le modifiche nel database
        db.session.commit()
        flash('Saldi trasferiti con successo per tutti gli utenti.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il trasferimento dei saldi: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))  # Redirigi alla dashboard admin


# Avvio dell'applicazione
if __name__ == '__main__':
    app.run(debug=True)
