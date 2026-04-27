from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models import models
from app.schemas import schemas
from app.core import auth, database

router = APIRouter(prefix="/talleres", tags=["Gestión de Talleres"])

@router.post("/", response_model=schemas.TallerOut)
def crear_taller(taller: schemas.TallerCreate, db: Session = Depends(database.get_db), 
                 current_user=Depends(auth.check_permissions("talleres.registrar"))):
    nuevo = models.Taller(**taller.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=List[schemas.TallerWithAdminOut])
def listar_talleres(db: Session = Depends(database.get_db)):
    """Lista todos los talleres incluyendo el nombre del administrador (propietario)."""
    results = db.query(models.Taller, models.Usuario.nombre.label("admin_nombre"))\
                .outerjoin(models.Usuario, (models.Taller.id == models.Usuario.taller_id) & (models.Usuario.rol == 'admin_taller'))\
                .all()
    
    talleres = []
    for taller, admin_nombre in results:
        taller_dict = schemas.TallerWithAdminOut.model_validate(taller)
        taller_dict.admin_nombre = admin_nombre or "Sin Asignar"
        talleres.append(taller_dict)
        
    return talleres


@router.get("/{id}", response_model=schemas.TallerOut)
def obtener_taller(id: int, db: Session = Depends(database.get_db)):
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return taller

@router.patch("/{id}/configuracion")
def configurar_taller_cu8(id: int, config: schemas.TallerUpdate, 
                         db: Session = Depends(database.get_db),
                         current_user=Depends(auth.get_current_user)):
    """CU8: Definir horarios y zonas de cobertura geográfica."""
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller: raise HTTPException(status_code=404)
    
    # Solo el dueño o SuperAdmin
    if current_user.rol != "super_admin" and current_user.taller_id != id:
        raise HTTPException(status_code=403, detail="No autorizado")

    if config.horarios_atencion: taller.horarios_atencion = config.horarios_atencion
    if config.poligono_cobertura: taller.poligono_cobertura = config.poligono_cobertura
    
    db.commit()
    return {"message": "Configuración de cobertura y horarios actualizada"}

@router.put("/{id}", response_model=schemas.TallerOut)
def actualizar_taller(id: int, taller_in: schemas.TallerUpdate, db: Session = Depends(database.get_db),
                      current_user=Depends(auth.get_current_user)):
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller: raise HTTPException(status_code=404, detail="Taller no encontrado")

    # Seguridad simplificada: SuperAdmin entra siempre, Admin_Taller solo al suyo
    if current_user.rol != "super_admin":
        if current_user.taller_id != id or current_user.rol != "admin_taller":
            raise HTTPException(status_code=403, detail="No tienes permiso para editar este taller")
    
    update_data = taller_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(taller, key, value)
        
    # Forzar la actualización del campo JSON en SQLAlchemy
    if "horarios_atencion" in update_data:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(taller, "horarios_atencion")
    
    db.commit()
    db.refresh(taller)
    return taller

@router.delete("/{id}")
def eliminar_taller(id: int, db: Session = Depends(database.get_db),
                    current_user=Depends(auth.check_permissions("talleres.registrar"))):
    taller = db.query(models.Taller).filter(models.Taller.id == id).first()
    if not taller: raise HTTPException(status_code=404, detail="Taller no encontrado")
    
    db.delete(taller)
    db.commit()
    return {"message": "Taller eliminado exitosamente"}
