"""
Bulk student registration from an Excel (.xlsx) or CSV roster.

Expected columns (header names are matched case-insensitively; common
variants such as "Email ID" or "Admission No" are accepted):

    Name | Email | Roll No | Class | Subjects | Electives | Password (optional)

* Subjects / Electives hold subject codes or names separated by "," ";" or "|".
  Unknown subjects are created on the fly (electives flagged as elective).
* Each student is enrolled in every listed subject — that is how electives are
  handled: two students in the same class can see different content.
* Initial password = the Password column if present, otherwise the roll number.
  Students are asked to change it at first login.
* Re-uploading the same sheet is safe: existing students are updated and new
  enrollments added, nothing is duplicated.
"""
import csv
import io
import re
import secrets

from openpyxl import Workbook, load_workbook
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.core.security import hash_password

HEADER_ALIASES = {
    "name": {"name", "full name", "student name", "student"},
    "email": {"email", "email id", "emailid", "e-mail", "mail", "email address"},
    "roll_no": {"roll no", "roll number", "rollno", "roll", "admission no", "admission number",
                "admin no", "school admin no", "school admission no", "registration no", "reg no"},
    "class_name": {"class", "section", "class/section", "class section", "class name", "batch"},
    "subjects": {"subjects", "core subjects", "subject", "subject codes"},
    "electives": {"electives", "elective", "elective subjects"},
    "password": {"password", "initial password"},
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm_header(h) -> str | None:
    key = re.sub(r"[_\.]+", " ", str(h or "")).strip().lower()
    key = re.sub(r"\s+", " ", key)
    for field, aliases in HEADER_ALIASES.items():
        if key in aliases:
            return field
    return None


def _read_rows(filename: str, data: bytes) -> list[dict]:
    if filename.lower().endswith(".csv"):
        text = data.decode("utf-8-sig", errors="ignore")
        raw_rows = list(csv.reader(io.StringIO(text)))
    else:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        raw_rows = [list(r) for r in ws.iter_rows(values_only=True)]
    if not raw_rows:
        return []
    headers = [_norm_header(h) for h in raw_rows[0]]
    if "email" not in headers:
        raise ValueError("The sheet needs an 'Email' column in the first row.")
    rows = []
    for i, raw in enumerate(raw_rows[1:], start=2):
        row = {"_row": i}
        for h, v in zip(headers, raw):
            if h:
                row[h] = "" if v is None else str(v).strip()
                if h == "roll_no" and row[h].endswith(".0"):   # Excel numeric roll numbers
                    row[h] = row[h][:-2]
        if any(v for k, v in row.items() if k != "_row"):
            rows.append(row)
    return rows


def _split(cell: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,;|/\n]+", cell or "") if p.strip()]


def _looks_like_code(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{2,6}[- ]?\d{2,4}[A-Za-z]?", token))


def _find_or_create_subject(db: Session, token: str, elective: bool, cache: dict, created: list) -> models.Subject:
    key = token.lower()
    if key in cache:
        return cache[key]
    subject = (
        db.query(models.Subject)
        .filter((func.lower(models.Subject.code) == key) | (func.lower(models.Subject.name) == key))
        .first()
    )
    if not subject:
        if _looks_like_code(token):
            code, name = token.upper().replace(" ", ""), token.upper()
        else:
            code = re.sub(r"[^A-Z0-9]+", "-", token.upper()).strip("-")[:24] or "SUBJECT"
            name = token
        subject = models.Subject(code=code, name=name, is_elective=elective)
        db.add(subject)
        db.flush()
        created.append(f"{subject.code} · {subject.name}{' (elective)' if elective else ''}")
    cache[key] = subject
    return subject


def import_roster(db: Session, filename: str, data: bytes) -> dict:
    settings = get_settings()
    rows = _read_rows(filename, data)
    created_users, updated_users, errors, generated = 0, 0, [], []
    subjects_created: list[str] = []
    enrollments_added = 0
    cache: dict = {}

    for row in rows:
        email = (row.get("email") or "").lower()
        if not EMAIL_RE.match(email):
            errors.append({"row": row["_row"], "error": f"Invalid or missing email: '{row.get('email', '')}'"})
            continue
        roll_no = row.get("roll_no") or None
        user = db.query(models.User).filter(models.User.email == email).first()
        if user and user.role != models.RoleEnum.student:
            errors.append({"row": row["_row"], "error": f"{email} already exists as {user.role.value}; skipped"})
            continue
        if roll_no:
            clash = db.query(models.User).filter(models.User.roll_no == roll_no, models.User.email != email).first()
            if clash:
                errors.append({"row": row["_row"], "error": f"Roll no {roll_no} already belongs to {clash.email}"})
                continue

        if not user:
            password = row.get("password") or roll_no or settings.default_student_password
            if not password:
                password = secrets.token_urlsafe(6)
                generated.append({"email": email, "password": password})
            user = models.User(
                email=email,
                hashed_password=hash_password(password),
                role=models.RoleEnum.student,
                must_change_password=not row.get("password"),
            )
            db.add(user)
            created_users += 1
        else:
            updated_users += 1
        if row.get("name"):
            user.full_name = row["name"]
        if roll_no:
            user.roll_no = roll_no
        if row.get("class_name"):
            user.class_name = row["class_name"]
        db.flush()

        existing = {e.subject_id for e in db.query(models.Enrollment).filter(models.Enrollment.user_id == user.id)}
        for elective, cell in ((False, row.get("subjects", "")), (True, row.get("electives", ""))):
            for token in _split(cell):
                subject = _find_or_create_subject(db, token, elective, cache, subjects_created)
                if subject.id not in existing:
                    db.add(models.Enrollment(user_id=user.id, subject_id=subject.id))
                    existing.add(subject.id)
                    enrollments_added += 1

    db.commit()
    return {
        "rows_read": len(rows),
        "students_created": created_users,
        "students_updated": updated_users,
        "enrollments_added": enrollments_added,
        "subjects_created": subjects_created,
        "errors": errors,
        "generated_passwords": generated,
        "password_rule": "Initial password is the Password column if given, otherwise the student's roll number. "
                         "Students can sign in with their email or roll number and are asked to change it.",
    }


def template_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    ws.append(["Name", "Email", "Roll No", "Class", "Subjects", "Electives", "Password"])
    ws.append(["Riya Sen", "riya.sen@school.edu", "23CS101", "CSE-2A", "CS201, CS202", "AI301", ""])
    ws.append(["Tarun Das", "tarun.das@school.edu", "23CS102", "CSE-2A", "CS201, CS202", "CS305", ""])
    ws.append(["Nisha Paul", "nisha.paul@school.edu", "23CS131", "CSE-2B", "CS201; CS202", "AI301", "Welcome@1"])
    for col, width in zip("ABCDEFG", (20, 30, 12, 10, 22, 16, 14)):
        ws.column_dimensions[col].width = width

    info = wb.create_sheet("How to fill")
    for line in [
        ["Column", "Required", "Notes"],
        ["Name", "recommended", "Student's full name"],
        ["Email", "yes", "Login id; must be unique"],
        ["Roll No", "recommended", "Roll / admission number. Also works as a login id and default password"],
        ["Class", "recommended", "Class/section, e.g. CSE-3A — used for class-level dashboards"],
        ["Subjects", "recommended", "Core subject codes or names, separated by commas"],
        ["Electives", "optional", "Elective subject codes or names — students only see electives they picked"],
        ["Password", "optional", "Leave blank to use the roll number as the first password"],
    ]:
        info.append(line)
    info.column_dimensions["A"].width = 12
    info.column_dimensions["B"].width = 14
    info.column_dimensions["C"].width = 90

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
