from app import db
from models import Holiday
from datetime import timedelta



def add_holiday_with_surrounding_days(holiday_date, weekday_cost=10):
    """
    Aggiunge un giorno festivo con costo zero e imposta un costo per i giorni lavorativi circostanti.

    :param holiday_date: Data del giorno festivo (datetime.date).
    :param weekday_cost: Costo in crediti per i giorni lavorativi circostanti.
    """
    # Aggiungi il giorno festivo con costo zero
    db.session.add(Holiday(date=holiday_date, cost=0))

    # Giorni lavorativi circostanti (lunedì-venerdì)
    offsets = [-1, 1]  # Giorni precedenti e successivi al giorno festivo
    for offset in offsets:
        surrounding_date = holiday_date + timedelta(days=offset)
        if surrounding_date.weekday() < 5:  # Controlla se è un giorno lavorativo
            existing_holiday = Holiday.query.filter_by(date=surrounding_date).first()
            if not existing_holiday:
                db.session.add(Holiday(date=surrounding_date, cost=weekday_cost))

    db.session.commit()
    print(f"Aggiunto giorno festivo: {holiday_date} e giorni circostanti.")




