import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    matricula = Column(String, index=True)
    cpf = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'ADMIN', 'SUPERVISOR', 'MOTORISTA', 'AJUDANTE'
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    password_hash = Column(String, nullable=False)
    status = Column(String, default="Ativo")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    records = relationship("PerformanceRecord", back_populates="user", cascade="all, delete-orphan")
    daily_records = relationship("DailyPerformanceRecord", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

class PerformanceRecord(Base):
    __tablename__ = "performance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    matricula = Column(String, nullable=False)
    competencia = Column(String, nullable=False, index=True)  # e.g., 'Julho/2026'
    cargo = Column(String, nullable=False)

    performance_pct = Column(Float, default=0.0)
    rv_prevista = Column(Float, default=0.0)
    rv_maxima = Column(Float, default=1000.0)
    ranking_pos = Column(Integer, default=1)
    ranking_total = Column(Integer, default=1)

    # 6 Operational Indicators
    caixas_val = Column(Float, default=0.0)
    caixas_meta = Column(Float, default=1000.0)
    caixas_pct = Column(Float, default=0.0)
    caixas_status = Column(String, default="VERDE")

    aderencia_raio_val = Column(Float, default=0.0)
    aderencia_raio_meta = Column(Float, default=100.0)
    aderencia_raio_pct = Column(Float, default=0.0)
    aderencia_raio_status = Column(String, default="VERDE")

    devolucao_val = Column(Float, default=0.0)
    devolucao_meta = Column(Float, default=2.0)
    devolucao_pct = Column(Float, default=0.0)
    devolucao_status = Column(String, default="VERDE")

    banco_horas_val = Column(String, default="00:00")
    banco_horas_meta = Column(String, default="20:00")
    banco_horas_he_cost = Column(Float, default=0.0)
    banco_horas_status = Column(String, default="VERDE")

    ponto_val = Column(String, default="100%")
    ponto_meta = Column(String, default="100%")
    ponto_pct = Column(Float, default=100.0)
    ponto_status = Column(String, default="VERDE")

    jornada_val = Column(String, default="Conforme")
    jornada_meta = Column(String, default="Conforme")
    jornada_pct = Column(Float, default=100.0)
    jornada_status = Column(String, default="VERDE")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="records")

class DailyPerformanceRecord(Base):
    __tablename__ = "daily_performance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    matricula = Column(String, nullable=False)
    competencia = Column(String, nullable=False, index=True)  # e.g., 'Julho/2026'
    date_str = Column(String, nullable=False)                  # e.g., '01/07/2026'
    day_num = Column(Integer, nullable=False)                   # e.g., 1
    rv_dia = Column(Float, default=0.0)
    rv_acumulada = Column(Float, default=0.0)
    caixas = Column(Float, default=0.0)
    mapa = Column(String, nullable=True)
    qtd_ajudantes = Column(Integer, default=1)
    hora_encerramento = Column(String, default="--:--")
    bateu_jl = Column(String, default="Sim")
    taxa_caixa = Column(Float, default=0.10)
    jornada_status = Column(String, default="VERDE")
    devolucao_status = Column(String, default="VERDE")
    raio_status = Column(String, default="VERDE")
    status_dia = Column(String, default="TRABALHADO")

    user = relationship("User", back_populates="daily_records")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    matricula = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    user_role = Column(String, nullable=False)
    competencia = Column(String, nullable=False, index=True)
    incident_date = Column(String, nullable=False)
    category = Column(String, nullable=False)
    comment = Column(Text, nullable=False)
    status = Column(String, default="PENDENTE")  # 'PENDENTE', 'EM ANÁLISE', 'RESOLVIDO'
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="feedbacks")

class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, default="Procedimentos Operacionais")  # 'Procedimentos Operacionais', 'Segurança', 'Atendimento ao Cliente', 'Outros'
    file_filename = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    file_data_base64 = Column(Text, nullable=True)
    uploaded_by_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    period = Column(String, nullable=False)
    goal = Column(String, nullable=False)
    prize = Column(String, nullable=False)
    progress_pct = Column(Float, default=0.0)
    status = Column(String, default="Em Andamento")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ImportHistory(Base):
    __tablename__ = "import_history"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    competencia = Column(String, nullable=False)
    total_records = Column(Integer, default=0)
    mot_count = Column(Integer, default=0)
    aju_count = Column(Integer, default=0)
    valid_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    error_details_json = Column(Text, nullable=True)
    imported_by_name = Column(String, nullable=False)
    imported_at = Column(DateTime, default=datetime.datetime.utcnow)
