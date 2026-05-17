from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.metrics import SCHEDULING_DURATION_MS, SCHEDULING_FAILURE_TOTAL, SCHEDULING_SUCCESS_TOTAL
from app.models import Shift, ShiftAssignment, ShiftSkillRequirement, Staff
from app.schemas import ScheduleRequest, ScheduleResponse, ShiftCreate, ShiftRead
from app.services.kafka_producer import produce_shift_event
from app.services.scheduler import solve_schedule

router = APIRouter(prefix='/shifts', tags=['shifts'])


@router.post('', response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreate, db: Session = Depends(get_db)):
    shift_data = payload.model_dump(exclude={'skill_requirements'})
    shift = Shift(**shift_data)
    db.add(shift)
    db.flush()
    for req in payload.skill_requirements:
        db.add(ShiftSkillRequirement(shift_id=shift.id, skill_id=req.skill_id, required_count=req.required_count))
    db.commit()
    db.refresh(shift)
    return shift


@router.get('', response_model=List[ShiftRead])
def list_shifts(status_filter: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Shift)
    if status_filter:
        query = query.filter(Shift.status == status_filter)
    return query.order_by(Shift.date).offset(skip).limit(limit).all()


@router.get('/{shift_id}', response_model=ShiftRead)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail='Shift not found')
    return shift


@router.put('/{shift_id}', response_model=ShiftRead)
def update_shift(shift_id: int, payload: ShiftCreate, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail='Shift not found')
    for f, v in payload.model_dump(exclude={'skill_requirements'}).items():
        setattr(shift, f, v)
    db.query(ShiftSkillRequirement).filter(ShiftSkillRequirement.shift_id == shift_id).delete()
    for req in payload.skill_requirements:
        db.add(ShiftSkillRequirement(shift_id=shift_id, skill_id=req.skill_id, required_count=req.required_count))
    db.commit()
    db.refresh(shift)
    return shift


@router.delete('/{shift_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail='Shift not found')
    db.delete(shift)
    db.commit()


@router.post('/schedule', response_model=ScheduleResponse)
def schedule_shifts(request: ScheduleRequest, db: Session = Depends(get_db)):
    shifts_orm = (
        db.query(Shift)
        .filter(Shift.id.in_(request.shift_ids))
        .options(
            selectinload(Shift.skill_requirements).selectinload(ShiftSkillRequirement.skill),
            selectinload(Shift.assignments),
        )
        .all()
    )
    if not shifts_orm:
        raise HTTPException(status_code=404, detail='No shifts found for the given IDs')

    staff_orm = (
        db.query(Staff)
        .filter(Staff.is_active == True)
        .options(selectinload(Staff.skills))
        .all()
    )

    shifts_data = [
        {
            'id': s.id,
            'date': s.date,
            'start_time': s.start_time,
            'end_time': s.end_time,
            'required_staff_count': s.required_staff_count,
            'skill_requirements': [{'skill_id': r.skill_id} for r in s.skill_requirements],
        }
        for s in shifts_orm
    ]

    staff_data = [
        {'id': st.id, 'skill_ids': [sk.id for sk in st.skills], 'max_hours_per_week': st.max_hours_per_week, 'is_active': st.is_active}
        for st in staff_orm
    ]

    assignments, elapsed_ms = solve_schedule(shifts_data, staff_data)
    SCHEDULING_DURATION_MS.observe(elapsed_ms)

    if assignments is None:
        SCHEDULING_FAILURE_TOTAL.inc()
        return ScheduleResponse(
            success=False, assignments=[], elapsed_ms=round(elapsed_ms, 2),
            message='No feasible schedule found. Ensure enough active staff possess the required skills and have sufficient hours.',
        )

    SCHEDULING_SUCCESS_TOTAL.inc()
    staff_map = {st.id: st for st in staff_orm}
    shift_map = {s.id: s for s in shifts_orm}

    for a in assignments:
        exists = db.query(ShiftAssignment).filter(
            ShiftAssignment.shift_id == a['shift_id'],
            ShiftAssignment.staff_id == a['staff_id'],
        ).first()
        if not exists:
            db.add(ShiftAssignment(shift_id=a['shift_id'], staff_id=a['staff_id']))

    for shift in shifts_orm:
        shift.status = 'scheduled'

    db.commit()

    for a in assignments:
        shift = shift_map.get(a['shift_id'])
        staff = staff_map.get(a['staff_id'])
        if shift and staff:
            produce_shift_event(
                event_type='SHIFT_ASSIGNED', shift_id=shift.id, staff_id=staff.id,
                shift_name=shift.name, staff_name=staff.name, shift_date=str(shift.date),
                start_time=str(shift.start_time), end_time=str(shift.end_time),
                location=shift.location or '',
            )

    return ScheduleResponse(
        success=True, assignments=assignments, elapsed_ms=round(elapsed_ms, 2),
        message=f'Scheduled {len(assignments)} assignments in {elapsed_ms:.1f} ms',
    )
