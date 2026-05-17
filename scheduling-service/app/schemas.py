from datetime import date, datetime, time
from typing import List, Optional
from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str
    description: Optional[str] = None


class SkillRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    model_config = {'from_attributes': True}


class StaffCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    max_hours_per_week: float = 40.0
    is_active: bool = True


class StaffRead(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    max_hours_per_week: float
    is_active: bool
    created_at: datetime
    skills: List[SkillRead] = []
    model_config = {'from_attributes': True}


class StaffBrief(BaseModel):
    id: int
    name: str
    email: str
    model_config = {'from_attributes': True}


class ShiftSkillRequirementCreate(BaseModel):
    skill_id: int
    required_count: int = Field(default=1, ge=1)


class ShiftSkillRequirementRead(BaseModel):
    id: int
    skill_id: int
    required_count: int
    skill: SkillRead
    model_config = {'from_attributes': True}


class AssignmentRead(BaseModel):
    id: int
    shift_id: int
    staff_id: int
    assigned_at: datetime
    staff: StaffBrief
    model_config = {'from_attributes': True}


class ShiftCreate(BaseModel):
    name: str
    date: date
    start_time: time
    end_time: time
    location: Optional[str] = None
    required_staff_count: int = Field(default=1, ge=1)
    status: str = 'unscheduled'
    skill_requirements: List[ShiftSkillRequirementCreate] = []


class ShiftRead(BaseModel):
    id: int
    name: str
    date: date
    start_time: time
    end_time: time
    location: Optional[str] = None
    required_staff_count: int
    status: str
    created_at: datetime
    skill_requirements: List[ShiftSkillRequirementRead] = []
    assignments: List[AssignmentRead] = []
    model_config = {'from_attributes': True}


class ScheduleRequest(BaseModel):
    shift_ids: List[int] = Field(..., min_length=1)


class ScheduleResponse(BaseModel):
    success: bool
    assignments: List[dict]
    elapsed_ms: float
    message: str
