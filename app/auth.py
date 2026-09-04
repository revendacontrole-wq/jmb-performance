import hmac
import hashlib
import base64
import json
import time
import re
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

security = HTTPBearer()

def clean_cpf(cpf_raw: str) -> str:
    """Strips all non-digit characters from CPF string."""
    if not cpf_raw:
        return ""
    return re.sub(r"\D", "", str(cpf_raw))

def mask_cpf(cpf_raw: str) -> str:
    """Formats CPF safely as ***.***.X55-66 without exposing full digits."""
    digits = clean_cpf(cpf_raw)
    if len(digits) < 11:
        digits = digits.zfill(11)
    if len(digits) >= 11:
        return f"***.***.{digits[6:9]}-{digits[9:11]}"
    return "***.***.***-**"

def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 password hashing."""
    salt = b"jmb_perf_salt_2026"
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return key.hex()

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against hash."""
    return hash_password(password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Creates a JWT token."""
    to_encode = data.copy()
    expire = int(time.time()) + (expires_delta or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    to_encode.update({"exp": expire})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
    
    signature_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(settings.SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        signature_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
        
        # Re-add padding for base64
        rem = len(sig_b64) % 4
        if rem > 0:
            sig_b64 += "=" * (4 - rem)
        actual_sig = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if parts[2] != actual_sig:
            return None
            
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
            
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        
        if payload.get("exp", 0) < int(time.time()):
            return None
            
        return payload
    except Exception:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Dependency to resolve current authenticated user."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sem identificação.")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
    return user

def require_role(roles: list):
    """RBAC dependency to restrict route to specified roles."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado para o seu perfil de usuário."
            )
        return current_user
    return role_checker
