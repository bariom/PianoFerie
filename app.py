from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from calendar import monthrange, day_name
from datetime import date, timedelta, datetime
from config import Config  # Importa la configurazione

from extensions import db, migrate

# Configurazione Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://planner_user:baro0014!@gvalug04/planner'
app.config['SECRET_KEY'] = 'your_secret_key'  # Cambia con una chiave sicura
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inizializza db e migrate
db.init_app(app)
migrate.init_app(app, db)

# Importa i modelli DOPO l'inizializzazione di db
from models import User, Holiday, Booking

# Decoratore per proteggere le route
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Devi effettuare il login per accedere a questa pagina.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


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
            session['user_id'] = user.id
            flash('Login effettuato con successo!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email o password errati.', 'danger')

    return render_template('login.html')


# Route Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('login'))


# Route Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Ottieni l'utente loggato
    user = User.query.get(session['user_id'])

    # Ottieni le ferie prenotate dall'utente
    bookings = Booking.query.filter_by(user_id=user.id).all()

    # Recupera le informazioni sulle date delle ferie prenotate
    booked_holidays = [
        {
            'date': Holiday.query.get(booking.holiday_id).date.strftime('%Y-%m-%d'),
            'cost': Holiday.query.get(booking.holiday_id).cost
        }
        for booking in bookings
    ]

    # Ottieni l'anno e il mese corrente per il link al calendario
    now = datetime.now()

    # Renderizza il template con i dati aggiornati
    return render_template(
        'dashboard.html',
        user=user,
        booked_holidays=booked_holidays,
        now=now
    )




# Route Prenotazione Ferie
@app.route('/book', methods=['POST'])
@login_required
def book_holiday():
    holiday_id = request.form.get('holiday_id')
    user = User.query.get(session['user_id'])
    holiday = Holiday.query.get(holiday_id)

    if user.credits >= holiday.cost:
        user.credits -= holiday.cost
        booking = Booking(user_id=user.id, holiday_id=holiday.id)
        db.session.add(booking)
        db.session.commit()

        flash('Ferie prenotate con successo!', 'success')
    else:
        flash('Crediti insufficienti.', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def employee_calendar_view(year, month):
    from calendar import Calendar

    user = User.query.get(session['user_id'])
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
                week_data.append({'date': None, 'cost': None, 'is_booked': False})
            else:
                current_date = date(year, month, day)
                holiday = holiday_data.get(current_date)
                if holiday:
                    cost = holiday.cost
                    holiday_id = holiday.id
                else:
                    cost = 10
                    holiday_id = None

                week_data.append({
                    'date': current_date,
                    'cost': cost,
                    'is_booked': Booking.query.filter_by(user_id=user.id, holiday_id=holiday_id).first() is not None
                })
        calendar_data.append(week_data)

    warnings = []  # Lista per i messaggi di warning

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





@app.route('/admin/calendar/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def admin_calendar(year, month):
    user = User.query.get(session['user_id'])

    # Verifica che l'utente sia amministratore
    if not user.is_admin:
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


# Avvio dell'applicazione
if __name__ == '__main__':
    app.run(debug=True)
