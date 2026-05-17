import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ShiftSlot:
    shift_id: int
    slot_index: int
    shift_date: object
    start_time: object
    end_time: object
    required_skill_ids: Set[int]
    duration_hours: float


@dataclass
class StaffNode:
    staff_id: int
    skill_ids: Set[int]
    max_hours_per_week: float
    assigned_shift_ids: Set[int] = field(default_factory=set)
    assigned_hours: float = 0.0


def _calc_duration(shift_date, start_time, end_time) -> float:
    start_dt = datetime.combine(shift_date, start_time)
    end_dt = datetime.combine(shift_date, end_time)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return (end_dt - start_dt).seconds / 3600.0


def _times_overlap(date1, s1, e1, date2, s2, e2) -> bool:
    if date1 != date2:
        return False
    return s1 < e2 and s2 < e1


def solve_schedule(
    shifts_data: List[dict],
    staff_data: List[dict],
) -> Tuple[Optional[List[dict]], float]:
    start_perf = time.perf_counter()

    shift_time_map: Dict[int, tuple] = {
        s['id']: (s['date'], s['start_time'], s['end_time'])
        for s in shifts_data
    }

    slots: List[ShiftSlot] = []
    for s in shifts_data:
        req_skills = {r['skill_id'] for r in s.get('skill_requirements', [])}
        dur = _calc_duration(s['date'], s['start_time'], s['end_time'])
        for idx in range(s['required_staff_count']):
            slots.append(ShiftSlot(
                shift_id=s['id'],
                slot_index=idx,
                shift_date=s['date'],
                start_time=s['start_time'],
                end_time=s['end_time'],
                required_skill_ids=req_skills,
                duration_hours=dur,
            ))

    staff_map: Dict[int, StaffNode] = {}
    for s in staff_data:
        if s.get('is_active', True):
            staff_map[s['id']] = StaffNode(
                staff_id=s['id'],
                skill_ids=set(s.get('skill_ids', [])),
                max_hours_per_week=s.get('max_hours_per_week', 40.0),
            )

    def is_feasible(staff: StaffNode, slot: ShiftSlot) -> bool:
        if slot.required_skill_ids and not slot.required_skill_ids.issubset(staff.skill_ids):
            return False
        for sid in staff.assigned_shift_ids:
            d2, s2, e2 = shift_time_map[sid]
            if _times_overlap(slot.shift_date, slot.start_time, slot.end_time, d2, s2, e2):
                return False
        if staff.assigned_hours + slot.duration_hours > staff.max_hours_per_week:
            return False
        return True

    def forward_check(from_idx: int, assignments: Dict) -> bool:
        for i in range(from_idx, len(slots)):
            slot = slots[i]
            already_in_shift: Set[int] = {
                sid for (sh_id, _), sid in assignments.items() if sh_id == slot.shift_id
            }
            has_candidate = any(
                staff.staff_id not in already_in_shift and is_feasible(staff, slot)
                for staff in staff_map.values()
            )
            if not has_candidate:
                return False
        return True

    def backtrack(idx: int, assignments: Dict) -> Optional[Dict]:
        if idx == len(slots):
            return dict(assignments)
        slot = slots[idx]
        already_in_shift: Set[int] = {
            sid for (sh_id, _), sid in assignments.items() if sh_id == slot.shift_id
        }
        for staff in staff_map.values():
            if staff.staff_id in already_in_shift:
                continue
            if not is_feasible(staff, slot):
                continue
            key = (slot.shift_id, slot.slot_index)
            assignments[key] = staff.staff_id
            staff.assigned_shift_ids.add(slot.shift_id)
            staff.assigned_hours += slot.duration_hours
            if forward_check(idx + 1, assignments):
                result = backtrack(idx + 1, assignments)
                if result is not None:
                    return result
            del assignments[key]
            staff.assigned_shift_ids.discard(slot.shift_id)
            staff.assigned_hours -= slot.duration_hours
        return None

    result = backtrack(0, {})
    elapsed_ms = (time.perf_counter() - start_perf) * 1000.0

    if result is None:
        return None, elapsed_ms

    output = [
        {'shift_id': sh_id, 'staff_id': staff_id}
        for (sh_id, _), staff_id in result.items()
    ]
    return output, elapsed_ms
