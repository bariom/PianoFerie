from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Inizializzazione delle estensioni
db = SQLAlchemy()
migrate = Migrate()
