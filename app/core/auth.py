import os
import random
import string
import re
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Usuario, RolPermiso, Permiso

SECRET_KEY = os.getenv("SECRET_KEY", "sos-automotriz-ultra-secret-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

import bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def validate_password_strength(password: str):
    """
    Valida que la contraseña cumpla con:
    - Mínimo 6 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un carácter especial
    """
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos una mayúscula")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos una minúscula")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos un número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos un carácter especial (!@#$%^&*...)")
    return True

def generate_recovery_code(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión expirada o inválida",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise credentials_exception
    except JWTError: raise credentials_exception
    
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user: raise credentials_exception
    return user

# --- ESTA ES LA FUNCIÓN QUE FALTABA ---
def get_permisos_por_rol(db: Session, rol: str) -> List[str]:
    """
    Obtiene la lista de códigos de permisos asociados a un rol.
    Crucial para que el Frontend sepa qué mostrar.
    """
    try:
        # Hacemos un join entre RolPermiso y Permiso para sacar solo los códigos (strings)
        permisos = db.query(Permiso.codigo).join(
            RolPermiso, RolPermiso.permiso_id == Permiso.id
        ).filter(RolPermiso.rol == rol).all()
        
        # Convertimos de lista de tuplas [('permiso',)] a lista simple ['permiso']
        return [p[0] for p in permisos]
    except Exception as e:
        print(f"Error al obtener permisos: {e}")
        return []

def check_permissions(permiso_requerido):
    """
    Verifica si el usuario tiene el permiso específico o uno de los roles permitidos.
    Soporta strings simples o listas de strings.
    """
    def decorator(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
        # Eliminamos el bypass para que todo sea validado por la matriz
        
        # Si permiso_requerido es una lista, checkeamos si el rol del usuario está en ella
        if isinstance(permiso_requerido, list):
            if current_user.rol in permiso_requerido:
                return current_user
            raise HTTPException(status_code=403, detail="No tienes el rol requerido")

        # Si es un string, buscamos en la matriz de permisos
        tiene_permiso = db.query(RolPermiso).join(Permiso).filter(
            RolPermiso.rol == current_user.rol,
            Permiso.codigo == permiso_requerido
        ).first()
        
        if not tiene_permiso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes el permiso: {permiso_requerido}"
            )
        return current_user
    return decorator