from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_admin():
    """
    Crea un utente amministratore nel database.
    """
    with app.app_context():  # Crea un contesto applicativo
        admin = User(
            name="Admin",
            email="admin@example.com",
            password_hash=generate_password_hash("next"),  # Cambia con la tua password desiderata
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Amministratore creato con successo!")

if __name__ == "__main__":
    create_admin()
