from datetime import datetime
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, String, Table, Text, Time, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


staff_skills = Table(
    'staff_skills',
    Base.metadata,
    Column('staff_id', Integer, ForeignKey('staff.id', ondelete='CASCADE'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True),
)


class Skill(Base):
    __tablename__ = 'skills'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    staff_members = relationship('Staff', secondary=staff_skills, back_populates='skills', lazy='selectin')
    shift_requirements = relationship('ShiftSkillRequirement', back_populates='skill', lazy='selectin')


class Staff(Base):
    __tablename__ = 'staff'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    max_hours_per_week = Column(Float, nullable=False, default=40.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    skills = relationship('Skill', secondary=staff_skills, back_populates='staff_members', lazy='selectin')
    assignments = relationship('ShiftAssignment', back_populates='staff', lazy='selectin', cascade='all, delete-orphan')


class Shift(Base):
    __tablename__ = 'shifts'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    location = Column(String(200), nullable=True)
    required_staff_count = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default='unscheduled')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    skill_requirements = relationship('ShiftSkillRequirement', back_populates='shift', lazy='selectin', cascade='all, delete-orphan')
    assignments = relationship('ShiftAssignment', back_populates='shift', lazy='selectin', cascade='all, delete-orphan')


class ShiftSkillRequirement(Base):
    __tablename__ = 'shift_skill_requirements'

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False)
    skill_id = Column(Integer, ForeignKey('skills.id', ondelete='CASCADE'), nullable=False)
    required_count = Column(Integer, nullable=False, default=1)

    __table_args__ = (UniqueConstraint('shift_id', 'skill_id', name='uq_shift_skill'),)

    shift = relationship('Shift', back_populates='skill_requirements')
    skill = relationship('Skill', back_populates='shift_requirements')


class ShiftAssignment(Base):
    __tablename__ = 'shift_assignments'

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False)
    staff_id = Column(Integer, ForeignKey('staff.id', ondelete='CASCADE'), nullable=False)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('shift_id', 'staff_id', name='uq_shift_assignment'),)

    shift = relationship('Shift', back_populates='assignments')
    staff = relationship('Staff', back_populates='assignments')
