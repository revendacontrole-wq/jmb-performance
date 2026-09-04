from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# --- Auth ---
class LoginRequest(BaseModel):
    cpf: str
    password: str

class UserProfileResponse(BaseModel):
    id: int
    matricula: Optional[str] = None
    name: str
    masked_cpf: str
    role: str
    status: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse

# --- Indicator Summary ---
class IndicatorItem(BaseModel):
    key: str
    label: str
    current_val: str
    meta_val: str
    pct: float
    status: str  # VERDE, AMARELO, VERMELHO
    impact_note: Optional[str] = None

# --- Breakdown / Entender Resultado ---
class ResultBreakdown(BaseModel):
    dentro_meta: List[str]
    fora_meta: List[str]
    fatores_reducao: List[str]
    potencial_restante: float
    rv_prevista: float
    rv_maxima: float

# --- Collaborator Dashboard ---
class CollaboratorDashboardResponse(BaseModel):
    name: str
    competencia: str
    performance_pct: float
    rv_prevista: float
    rv_maxima: float
    ranking_pos: int
    ranking_total: int
    indicators: List[IndicatorItem]
    breakdown: ResultBreakdown
    available_competencias: List[str]

# --- Monthly History Item ---
class HistoryItem(BaseModel):
    competencia: str
    performance_pct: float
    rv_prevista: float
    ranking_pos: int
    status_geral: str

# --- Supervisor Team Member ---
class TeamMemberItem(BaseModel):
    id: int
    matricula: Optional[str] = None
    name: str
    role: str
    masked_cpf: str
    performance_pct: float
    rv_prevista: float
    status: str
    ranking_pos: int

class SupervisorDashboardResponse(BaseModel):
    total_members: int
    dentro_meta: int
    em_atencao: int
    fora_meta: int
    team: List[TeamMemberItem]

# --- Feedback Schemas ---
class FeedbackCreateRequest(BaseModel):
    competencia: str
    incident_date: str
    category: str
    comment: str

class FeedbackItem(BaseModel):
    id: int
    user_id: int
    matricula: str
    user_name: str
    user_role: str
    competencia: str
    incident_date: str
    category: str
    comment: str
    status: str
    admin_notes: Optional[str] = None
    created_at: str

class FeedbackStatusUpdateRequest(BaseModel):
    status: str
    admin_notes: Optional[str] = None

# --- Training Schemas ---
class TrainingItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    file_filename: str
    file_url: str
    file_size_formatted: str
    uploaded_by_name: str
    created_at: str

    class Config:
        from_attributes = True

# --- Excel Preview Schemas ---
class ImportErrorDetail(BaseModel):
    aba: str
    colaborador: str
    campo: str
    problema: str

class RecordSample(BaseModel):
    matricula: str
    nome: str
    cargo: str
    masked_cpf: str
    performance_pct: float
    rv_prevista: float
    rv_maxima: float
    status: str
    indicadores_count: int

class PreviewResponse(BaseModel):
    competencia: str
    mot_found: int
    aju_found: int
    valid_count: int
    error_count: int
    new_records: int
    update_records: int
    errors: List[ImportErrorDetail]
    sample: List[RecordSample]
    file_token: str

class ConfirmImportRequest(BaseModel):
    file_token: str
    competencia: str

class ImportConfirmResponse(BaseModel):
    success: bool
    message: str
    competencia: str
    total_processed: int
    created_users: int
    updated_users: int

class ImportHistoryItem(BaseModel):
    id: int
    filename: str
    competencia: str
    total_records: int
    mot_count: int
    aju_count: int
    valid_count: int
    error_count: int
    created_count: int
    updated_count: int
    imported_by_name: str
    created_at: str

class UserSummary(BaseModel):
    id: int
    matricula: str
    name: str
    role: str
    masked_cpf: str
    status: str
