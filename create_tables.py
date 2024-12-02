from app import app, db

def create_tables():
    """
    Crea tutte le tabelle definite nei modelli, se non esistono.
    """
    with app.app_context():
        try:
            # Verifica e crea tabelle solo se non esistono
            db.create_all()
            print("Tabelle create con successo!")
        except Exception as e:
            print(f"Errore durante la creazione delle tabelle: {e}")

if __name__ == "__main__":
    create_tables()
