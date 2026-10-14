"""Plain-Python lookups over the fictional campus records in data/.

No agents or Opik in here: every function takes simple arguments and returns a
dict, so the unit tests can exercise them directly. main.py wraps them as tools.
"""

import json
import uuid
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def _load(name: str):
    return json.loads((DATA_DIR / f"{name}.json").read_text())


def _unknown(student_id: str) -> dict:
    return {"error": f"no student with id {student_id}"}


def _known(student_id: str) -> bool:
    return any(s["id"] == student_id for s in _load("students"))


# --- housing ---------------------------------------------------------------

def housing_assignment(student_id: str) -> dict:
    if not _known(student_id):
        return _unknown(student_id)
    for row in _load("housing")["assignments"]:
        if row["student_id"] == student_id:
            if row["hall"] is None:
                return {"student_id": student_id, "assignment": None,
                        "note": "student is not currently in university housing"}
            return row
    return _unknown(student_id)


def housing_vacancies(max_rent_per_month: float, room_type: str = "") -> dict:
    rooms = [
        v for v in _load("housing")["vacancies"]
        if v["rent_per_month"] <= max_rent_per_month
        and (not room_type or v["type"] == room_type.lower())
    ]
    return {"vacancies": rooms} if rooms else {"error": "no vacancies match"}


def room_change_request(student_id: str, hall: str, room: str) -> dict:
    if not _known(student_id):
        return _unknown(student_id)
    target = [v for v in _load("housing")["vacancies"]
              if v["hall"].lower() == hall.lower() and v["room"] == room]
    if not target:
        return {"error": f"{hall} {room} is not a vacant room"}
    return {"status": "submitted", "student_id": student_id, "hall": target[0]["hall"],
            "room": room, "ticket": f"HSG-{uuid.uuid4().hex[:6].upper()}"}


# --- financial aid ---------------------------------------------------------

def aid_package(student_id: str) -> dict:
    for row in _load("financial_aid")["packages"]:
        if row["student_id"] == student_id:
            total = row["grant"] + row["scholarship"] + row["loan_offered"] + row["work_study"]
            return {**row, "total_offered": total,
                    "free_money": row["grant"] + row["scholarship"]}
    return _unknown(student_id)


def aid_tasks(student_id: str) -> dict:
    if not _known(student_id):
        return _unknown(student_id)
    tasks = [t for t in _load("financial_aid")["tasks"] if t["student_id"] == student_id]
    return {"student_id": student_id, "tasks": tasks,
            "deadlines": _load("financial_aid")["deadlines"]}


# --- registrar -------------------------------------------------------------

def class_schedule(student_id: str) -> dict:
    for row in _load("registrar")["enrollments"]:
        if row["student_id"] == student_id:
            credits = sum(c["credits"] for c in row["courses"])
            return {**row, "total_credits": credits}
    return _unknown(student_id)


def account_holds(student_id: str) -> dict:
    if not _known(student_id):
        return _unknown(student_id)
    holds = [h for h in _load("registrar")["holds"] if h["student_id"] == student_id]
    return {"student_id": student_id, "holds": holds,
            "add_drop_deadline": _load("registrar")["add_drop_deadline"],
            "withdrawal_deadline": _load("registrar")["withdrawal_deadline"]}
