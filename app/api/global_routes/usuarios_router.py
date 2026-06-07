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
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_taller"]))
):
    """Endpoint CU6: SuperAdmin/AdminTaller crea usuarios (ej. Técnicos)."""
    if db.query(models.Usuario).filter(models.Usuario.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    if current_user.rol in ["admin_taller", "admin_empresa"]:
        if current_user.rol == "admin_taller" and user_in.rol not in ["tecnico", "admin_taller"]:
            raise HTTPException(status_code=403, detail="Solo puedes crear técnicos o administradores")
        user_in.empresa_id = current_user.empresa_id # Forzamos que sea de la misma empresa
    
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
