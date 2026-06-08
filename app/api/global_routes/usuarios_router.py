from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import global_models as models
from app.schemas import global_schemas as schemas
from app.core import auth, database

router = APIRouter(prefix="/usuarios", tags=["Gestión de Usuarios"])

@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    user_in: schemas.UserCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_empresa", "admin_taller"]))
):
    """Endpoint CU6: SuperAdmin/AdminEmpresa/AdminTaller crea usuarios (ej. Técnicos)."""
    if db.query(models.Usuario).filter(models.Usuario.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # === VERIFICACIONES DE ROL ===
    if current_user.rol == "admin_taller":
        if user_in.rol != "tecnico":
            raise HTTPException(status_code=403, detail="Solo puedes crear técnicos para tu taller")
        user_in.taller_id = current_user.taller_id # Inyección forzada de seguridad

    elif current_user.rol == "admin_empresa":
        if user_in.rol not in ["admin_taller", "tecnico"]:
            raise HTTPException(status_code=403, detail="Solo puedes crear administradores de taller o técnicos")
            
        if user_in.rol == "admin_taller" and not user_in.taller_id:
            raise HTTPException(status_code=400, detail="Debes asignar un taller al administrador de taller")

    elif current_user.rol == "super_admin":
        pass 
        
    else:
        raise HTTPException(status_code=403, detail="No tienes permisos para crear usuarios")

    # Inyectar la misma empresa
    if current_user.rol in ["admin_taller", "admin_empresa"]:
        user_in.empresa_id = current_user.empresa_id
        
    # === VERIFICACIÓN DE LÍMITES DE SUSCRIPCIÓN PARA TÉCNICOS ===
    if user_in.rol == "tecnico" and current_user.empresa:
        suscripcion = current_user.empresa.suscripcion
        if suscripcion:
            max_tecnicos = suscripcion.max_tecnicos
            tecnicos_actuales = db.query(models.Usuario).filter(
                models.Usuario.empresa_id == current_user.empresa_id,
                models.Usuario.rol == "tecnico"
            ).count()
            
            if tecnicos_actuales >= max_tecnicos:
                raise HTTPException(
                    status_code=402, 
                    detail=f"Has alcanzado el límite de {max_tecnicos} técnicos de tu plan. Actualiza tu suscripción."
                )
    
    # Validar fortaleza de contraseña
    auth.validate_password_strength(user_in.password)

    nuevo_usuario = models.Usuario(
        nombre=user_in.nombre,
        email=user_in.email,
        telefono=user_in.telefono,
        rol=user_in.rol,
        empresa_id=user_in.empresa_id,
        taller_id=user_in.taller_id,
        password_hash=auth.get_password_hash(user_in.password)
    )
    db.add(nuevo_usuario)
    db.commit()
    
    from sqlalchemy import text
    db.execute(text("SET search_path TO public"))
    db.refresh(nuevo_usuario)
    
    # Nota: La creación del perfil Tecnico se delega a las rutas tenant 
    # cuando el técnico se asigne a un taller.

    return nuevo_usuario

@router.get("/", response_model=List[schemas.UserOut])
def listar_usuarios(
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions("usuarios.gestionar.ver"))
):
    """Listado general de usuarios."""
    if current_user.rol == "super_admin":
        users = db.query(models.Usuario).all()
    else:
        users = db.query(models.Usuario).filter(models.Usuario.empresa_id == current_user.empresa_id).all()
    return users

@router.get("/taller/{taller_id}/tecnicos", response_model=List[schemas.UserOut])
def listar_tecnicos_taller(
    taller_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Obtiene los técnicos asignados a un taller específico."""
    # Validación de seguridad básica
    if current_user.rol == "admin_taller" and current_user.taller_id != taller_id:
        raise HTTPException(status_code=403, detail="No puedes ver técnicos de otros talleres")
    
    if current_user.rol not in ["super_admin", "admin_empresa", "admin_taller"]:
        raise HTTPException(status_code=403, detail="No autorizado")

    users = db.query(models.Usuario).filter(
        models.Usuario.taller_id == taller_id,
        models.Usuario.rol == "tecnico"
    ).all()
    return users

@router.put("/{usuario_id}", response_model=schemas.UserOut)
def actualizar_perfil(
    usuario_id: int, 
    data: schemas.UserUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions("usuarios.perfil.modificar"))
):
    user_query = db.query(models.Usuario).filter(models.Usuario.id == usuario_id)
    user = user_query.first()
    if not user: 
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if current_user.rol != "super_admin" and user.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar usuarios de otra empresa")

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("password"):
        auth.validate_password_strength(update_data["password"])
        update_data["password_hash"] = auth.get_password_hash(update_data.pop("password"))
    
    user_query.update(update_data, synchronize_session=False)
    db.commit()
    from sqlalchemy import text
    db.execute(text("SET search_path TO public"))
    db.refresh(user)
    return user

@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, db: Session = Depends(database.get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if current_user.rol != "super_admin" and user.empresa_id != current_user.empresa_id:
        raise HTTPException(status_code=403, detail="No puedes eliminar usuarios de otra empresa")

    db.delete(user)
    db.commit()
    return None
