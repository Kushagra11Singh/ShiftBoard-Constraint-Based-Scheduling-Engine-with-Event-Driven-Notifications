from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Skill
from app.schemas import SkillCreate, SkillRead

router = APIRouter(prefix='/skills', tags=['skills'])


@router.post('', response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)):
    if db.query(Skill).filter(Skill.name == payload.name).first():
        raise HTTPException(status_code=400, detail='Skill already exists')
    skill = Skill(**payload.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get('', response_model=List[SkillRead])
def list_skills(db: Session = Depends(get_db)):
    return db.query(Skill).all()


@router.get('/{skill_id}', response_model=SkillRead)
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail='Skill not found')
    return skill


@router.put('/{skill_id}', response_model=SkillRead)
def update_skill(skill_id: int, payload: SkillCreate, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail='Skill not found')
    for f, v in payload.model_dump().items():
        setattr(skill, f, v)
    db.commit()
    db.refresh(skill)
    return skill


@router.delete('/{skill_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail='Skill not found')
    db.delete(skill)
    db.commit()
