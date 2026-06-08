from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.models import global_models as models
from app.schemas import global_schemas as schemas
from app.core import database, auth

router = APIRouter(prefix="/suscripciones", tags=["Gestión de Suscripciones (SaaS)"])

@router.get("/", response_model=List[schemas.SuscripcionOut])
def listar_suscripciones(db: Session = Depends(database.get_db),
                         current_user: models.Usuario = Depends(auth.check_permissions(["super_admin_global"]))):
    """Lista todas las suscripciones disponibles (solo SuperAdmin)."""
    return db.query(models.Suscripcion).all()
