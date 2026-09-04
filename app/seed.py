from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models import User, PerformanceRecord, Campaign, ImportHistory
from app.auth import hash_password, clean_cpf

def seed_database():
    """Initializes SQLite database tables and seeds single clean Admin user."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Create single clean Admin user if missing
        admin = db.query(User).filter(User.cpf == "00000000000").first()
        if not admin:
            admin = User(
                matricula="001",
                cpf="00000000000",
                name="Administrador JMB",
                role="ADMIN",
                password_hash=hash_password("admin2026"),
                status="Ativo"
            )
            db.add(admin)
            db.flush()

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
