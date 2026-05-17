from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Skill, Staff
from app.schemas import StaffCreate, StaffRead

router = APIRouter(prefix='/staff', tags=['staff'])


@router.post('', response_model=StaffRead, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db)):
    if db.query(Staff).filter(Staff.email == payload.email).first():
        raise HTTPException(status_code=400, detail='Email already registered')
    staff = Staff(**payload.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get('', response_model=List[StaffRead])
def list_staff(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Staff).offset(skip).limit(limit).all()


@router.get('/{staff_id}', response_model=StaffRead)
def get_staff(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail='Staff member not found')
    return staff


@router.put('/{staff_id}', response_model=StaffRead)
def update_staff(staff_id: int, payload: StaffCreate, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail='Staff member not found')
    if payload.email != staff.email:
        if db.query(Staff).filter(Staff.email == payload.email).first():
            raise HTTPException(status_code=400, detail='Email already registered')
    for f, v in payload.model_dump().items():
        setattr(staff, f, v)
    db.commit()
    db.refresh(staff)
    return staff


@router.delete('/{staff_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail='Staff member not found')
    db.delete(staff)
    db.commit()


@router.post('/{staff_id}/skills/{skill_id}', response_model=StaffRead)
def add_skill_to_staff(staff_id: int, skill_id: int, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail='Staff member not found')
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail='Skill not found')
    if skill not in staff.skills:
        staff.skills.append(skill)
        db.commit()
        db.refresh(staff)
    return staff


@router.delete('/{staff_id}/skills/{skill_id}', response_model=StaffRead)
def remove_skill_from_staff(staff_id: int, skill_id: int, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail='Staff member not found')
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail='Skill not found')
    if skill in staff.skills:
        staff.skills.remove(skill)
        db.commit()
        db.refresh(staff)
    return staff
