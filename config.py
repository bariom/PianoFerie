#DEFAULT_COST = 10  # Costo di una giornata normale
#DEFAULT_CREDITS = 410  # Crediti iniziali per ogni dipendente (12,42 crediti a giorno)
#HIGH_DEMAND_COST = 15  # Costo per giorni ad alta richiesta
#HOLIDAY_COST = 20  # Costo per festività principali
class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://planner_user:baro0014!@gvalug04/planner'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_COST = 10  # Valore predefinito per i costi

