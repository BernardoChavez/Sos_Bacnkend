from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import global_models as models
from app.schemas import global_schemas as schemas
from app.core import auth, database, mailer
from app.core.audit_logger import registrar_auditoria

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=schemas.Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    # 1. Buscar usuario
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    # 2. Verificar si está bloqueado temporalmente
    ahora = datetime.utcnow()
    if user.bloqueado_hasta and ahora < user.bloqueado_hasta:
        tiempo_restante = int((user.bloqueado_hasta - ahora).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Cuenta bloqueada temporalmente. Intenta en {tiempo_restante} segundos."
        )

    # 3. Verificar contraseña
    if not auth.verify_password(form_data.password, user.password_hash):
        # Incrementar intentos fallidos
        user.intentos_fallidos += 1
        
        if user.intentos_fallidos >= 3:
            user.bloqueado_hasta = ahora + timedelta(minutes=1)
            user.intentos_fallidos = 0 
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demasiados intentos fallidos. Tu cuenta ha sido bloqueada por 1 minuto."
            )
        
        db.commit()
        intentos_restantes = 3 - user.intentos_fallidos
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Contraseña incorrecta. Te quedan {intentos_restantes} intentos."
        )
    
    # 4. Login exitoso -> Reiniciar contadores
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    db.commit()
    
    lista_permisos = auth.get_permisos_por_rol(db, user.rol)
    
    access_token = auth.create_access_token(
        data={
            "sub": user.email, 
            "rol": user.rol, 
            "id": user.id, 
            "taller_id": user.taller_id,
            "permisos": lista_permisos
        }
    )
    
    user_data = {
        "id": user.id,
        "nombre": user.nombre,
        "email": user.email,
        "rol": user.rol,
        "empresa_id": user.empresa_id,
        "taller_id": user.taller_id,
        "telefono": user.telefono,
        "permisos": lista_permisos
    }

    # AUDITORIA: Registrar inicio de sesión (Necesario aquí porque aún no hay Token para el Middleware)
    registrar_auditoria(request, user.id, "POST", f"Inicio de sesión: Acceso concedido a {user.nombre}")

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_data
    }

@router.post("/logout")
def logout(request: Request, db: Session = Depends(database.get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Cierra la sesión y registra la acción en la bitácora."""
    # El registro de auditoria ahora se maneja automaticamente por el Middleware global
    return {"message": "Sesión cerrada correctamente"}

@router.get("/me", response_model=schemas.UserOut)
def get_me(db: Session = Depends(database.get_db), current_user=Depends(auth.get_current_user)):
    lista_permisos = auth.get_permisos_por_rol(db, current_user.rol)
    user_out = schemas.UserOut.model_validate(current_user)
    user_out.permisos = lista_permisos
    return user_out

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    user_exist = db.query(models.Usuario).filter(models.Usuario.email == user_in.email).first()
    if user_exist:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    
    # Validar fortaleza de contraseña
    auth.validate_password_strength(user_in.password)
    
    user_in.rol = "cliente"
    nuevo_usuario = models.Usuario(
        nombre=user_in.nombre,
        email=user_in.email,
        telefono=user_in.telefono,
        rol=user_in.rol,
        password_hash=auth.get_password_hash(user_in.password)
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.post("/recover-password", status_code=status.HTTP_200_OK)
async def recover_password(data: schemas.PasswordRecover, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == data.email).first()
    if not user:
        return {"message": "Si el correo está registrado, recibirás un código pronto."}
    code = auth.generate_recovery_code()
    user.recovery_code = code
    db.commit()
    background_tasks.add_task(mailer.send_recovery_email, user.email, code)
    return {"message": "Si el correo está registrado, recibirás un código pronto."}

@router.post("/verify-code", status_code=status.HTTP_200_OK)
def verify_code(data: schemas.PasswordVerifyCode, db: Session = Depends(database.get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == data.email, models.Usuario.recovery_code == data.code).first()
    if not user:
        raise HTTPException(status_code=400, detail="Código inválido o correo incorrecto")
    return {"message": "Código verificado correctamente"}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(data: schemas.PasswordResetCode, db: Session = Depends(database.get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == data.email, models.Usuario.recovery_code == data.code).first()
    if not user:
        raise HTTPException(status_code=400, detail="Operación no permitida")
    
    # Validar fortaleza de la nueva contraseña
    auth.validate_password_strength(data.new_password)
    
    user.password_hash = auth.get_password_hash(data.new_password)
    user.recovery_code = None
    db.commit()
    return {"message": "Contraseña restablecida exitosamente"}
