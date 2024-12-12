#DEFAULT_COST = 10  # Costo di una giornata normale
#DEFAULT_CREDITS = 410  # Crediti iniziali per ogni dipendente (12,42 crediti a giorno)
#HIGH_DEMAND_COST = 15  # Costo per giorni ad alta richiesta
#HOLIDAY_COST = 20  # Costo per festività principali
class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://planner_user:baro0014!@gvalug04/planner'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_COST = 10  # Valore predefinito per i costi
    INACTIVITY_TIMEOUT = 5 * 60  # 5 min in secondi
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 5,
        'pool_timeout': 30,
        'max_overflow': 10
    }

