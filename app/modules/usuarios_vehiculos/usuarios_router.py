from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import models
from app.schemas import schemas
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

    if current_user.rol == "admin_taller":
        if user_in.rol not in ["tecnico", "admin_taller"]:
            raise HTTPException(status_code=403, detail="Solo puedes crear técnicos o administradores")
        user_in.taller_id = current_user.taller_id
    
    # Validar fortaleza de contraseña
    auth.validate_password_strength(user_in.password)

    nuevo_usuario = models.Usuario(
        nombre=user_in.nombre,
        email=user_in.email,
        telefono=user_in.telefono,
        rol=user_in.rol,
        taller_id=user_in.taller_id,
        password_hash=auth.get_password_hash(user_in.password)
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    if nuevo_usuario.rol == "tecnico":
        ficha_tecnico = models.Tecnico(
            usuario_id=nuevo_usuario.id,
            taller_id=nuevo_usuario.taller_id,
            disponible=True,
            especialidad_principal="General"
        )
        db.add(ficha_tecnico)
        db.commit()
    
    return nuevo_usuario

@router.get("/", response_model=List[schemas.UserWithTallerOut])
def listar_usuarios(
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions("usuarios.gestionar.ver"))
):
    """Listado general de usuarios con su taller, solo para Super Admin."""
    results = db.query(models.Usuario, models.Taller.nombre.label("taller_nombre"))\
                .outerjoin(models.Taller, models.Usuario.taller_id == models.Taller.id).all()
    
    users = []
    for u, taller_nombre in results:
        user_dict = {
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "telefono": u.telefono,
            "rol": u.rol,
            "taller_id": u.taller_id,
            "taller_nombre": taller_nombre if taller_nombre else "N/A"
        }
        users.append(user_dict)
    return users

@router.get("/taller/{taller_id}/tecnicos", response_model=List[schemas.UserWithTallerOut])
def listar_tecnicos_taller(
    taller_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(auth.check_permissions(["super_admin", "admin_taller"]))
):
    """Endpoint CU6: Admin_Taller lista a todos los usuarios con rol tecnico de su taller"""
    if current_user.rol == "admin_taller" and current_user.taller_id != taller_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a los técnicos de otro taller")
        
    results = db.query(models.Usuario, models.Taller.nombre, models.Tecnico.disponible, models.Tecnico.id.label("tecnico_id"))\
              .outerjoin(models.Taller, models.Usuario.taller_id == models.Taller.id)\
              .outerjoin(models.Tecnico, models.Usuario.id == models.Tecnico.usuario_id)\
              .filter(models.Usuario.taller_id == taller_id, models.Usuario.rol == "tecnico").all()
    
    users = []
    for u, taller_nombre, disponible, tecnico_id in results:
        if tecnico_id is None:
            nueva_ficha = models.Tecnico(
                usuario_id=u.id, 
                taller_id=u.taller_id, 
                disponible=True,
                especialidad_principal="General"
            )
            db.add(nueva_ficha)
            db.commit()
            db.refresh(nueva_ficha)
            tecnico_id = nueva_ficha.id
            disponible = True
            
        users.append({
            "id": tecnico_id,
            "usuario_id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "telefono": u.telefono,
            "rol": u.rol,
            "taller_id": u.taller_id,
            "taller_nombre": taller_nombre if taller_nombre else "Mi Taller",
            "disponible": disponible
        })
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
    
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("password"):
        # Validar fortaleza de la nueva contraseña
        auth.validate_password_strength(update_data["password"])
        update_data["password_hash"] = auth.get_password_hash(update_data.pop("password"))
    
    user_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
    return None
