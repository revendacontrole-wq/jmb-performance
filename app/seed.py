from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import engine, SessionLocal, Base
from app.models import User, PerformanceRecord, Campaign, ImportHistory, Training, DailyPerformanceRecord, ExtraIndicatorRecord
from app.auth import hash_password, clean_cpf

def seed_database():
    """Initializes SQLite database tables and seeds single clean Admin user."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Schema migration check for SQLite tables
        migrations = [
            "ALTER TABLE performance_records ADD COLUMN rating VARCHAR DEFAULT 'Rating B'",
            "ALTER TABLE performance_records ADD COLUMN caixas_val FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN caixas_meta FLOAT DEFAULT 1000.0",
            "ALTER TABLE performance_records ADD COLUMN caixas_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN caixas_status VARCHAR DEFAULT 'VERDE'",
            "ALTER TABLE performance_records ADD COLUMN aderencia_raio_val FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN aderencia_raio_meta FLOAT DEFAULT 100.0",
            "ALTER TABLE performance_records ADD COLUMN aderencia_raio_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN aderencia_raio_status VARCHAR DEFAULT 'VERDE'",
            "ALTER TABLE performance_records ADD COLUMN devolucao_val FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN devolucao_meta FLOAT DEFAULT 2.0",
            "ALTER TABLE performance_records ADD COLUMN devolucao_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN devolucao_status VARCHAR DEFAULT 'VERDE'",
            "ALTER TABLE performance_records ADD COLUMN banco_horas_val VARCHAR DEFAULT '00:00'",
            "ALTER TABLE performance_records ADD COLUMN banco_horas_meta VARCHAR DEFAULT '20:00'",
            "ALTER TABLE performance_records ADD COLUMN banco_horas_he_cost FLOAT DEFAULT 0.0",
            "ALTER TABLE performance_records ADD COLUMN banco_horas_status VARCHAR DEFAULT 'VERDE'",
            "ALTER TABLE performance_records ADD COLUMN ponto_val VARCHAR DEFAULT '100%'",
            "ALTER TABLE performance_records ADD COLUMN ponto_meta VARCHAR DEFAULT '100%'",
            "ALTER TABLE performance_records ADD COLUMN ponto_pct FLOAT DEFAULT 100.0",
            "ALTER TABLE performance_records ADD COLUMN ponto_status VARCHAR DEFAULT 'VERDE'",
            "ALTER TABLE performance_records ADD COLUMN jornada_val VARCHAR DEFAULT 'Conforme'",
            "ALTER TABLE performance_records ADD COLUMN jornada_meta VARCHAR DEFAULT 'Conforme'",
            "ALTER TABLE performance_records ADD COLUMN jornada_pct FLOAT DEFAULT 100.0",
            "ALTER TABLE performance_records ADD COLUMN jornada_status VARCHAR DEFAULT 'VERDE'",
            "ALTER TABLE daily_performance_records ADD COLUMN taxa_caixa FLOAT DEFAULT 0.10",
            "ALTER TABLE trainings ADD COLUMN file_data_base64 TEXT",
            "ALTER TABLE trainings ADD COLUMN file_size_bytes INTEGER DEFAULT 0"
        ]

        for stmt in migrations:
            try:
                db.execute(text(stmt))
                db.commit()
            except Exception:
                db.rollback()

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
