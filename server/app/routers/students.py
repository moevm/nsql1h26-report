import time
import datetime
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query, run_write

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="client/templates")


def _next_id() -> int:
    result = run_query("MATCH (s:Student) RETURN max(s.id) AS max_id")
    max_id = result[0]["max_id"] if result and result[0]["max_id"] is not None else 0
    return int(max_id) + 1


def _fmt_ts(ts):
    if not ts:
        return "—"
    return datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")


def _parse_dt(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M").timestamp())
    except ValueError:
        return None


@router.get("/")
async def students_list(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    params = dict(request.query_params)

    having_conditions = []
    where_conditions = []
    query_params = {}

    name = params.get("name", "").strip()
    if name:
        where_conditions.append("toLower(s.name) CONTAINS toLower($name)")
        query_params["name"] = name

    surname = params.get("surname", "").strip()
    if surname:
        where_conditions.append("toLower(s.surname) CONTAINS toLower($surname)")
        query_params["surname"] = surname

    group = params.get("group", "").strip()
    if group and group.isdigit():
        where_conditions.append("s.group = $group")
        query_params["group"] = int(group)

    min_reports = params.get("min_reports", "").strip()
    if min_reports and min_reports.isdigit():
        having_conditions.append("report_count >= $min_reports")
        query_params["min_reports"] = int(min_reports)

    max_reports = params.get("max_reports", "").strip()
    if max_reports and max_reports.isdigit():
        having_conditions.append("report_count <= $max_reports")
        query_params["max_reports"] = int(max_reports)

    last_upload_from = _parse_dt(params.get("last_upload_from", ""))
    if last_upload_from is not None:
        having_conditions.append("last_upload >= $last_upload_from")
        query_params["last_upload_from"] = last_upload_from

    last_upload_to = _parse_dt(params.get("last_upload_to", ""))
    if last_upload_to is not None:
        having_conditions.append("last_upload <= $last_upload_to")
        query_params["last_upload_to"] = last_upload_to

    created_from = _parse_dt(params.get("created_from", ""))
    if created_from is not None:
        where_conditions.append("s.created_at >= $created_from")
        query_params["created_from"] = created_from

    created_to = _parse_dt(params.get("created_to", ""))
    if created_to is not None:
        where_conditions.append("s.created_at <= $created_to")
        query_params["created_to"] = created_to

    updated_from = _parse_dt(params.get("updated_from", ""))
    if updated_from is not None:
        where_conditions.append("s.updated_at >= $updated_from")
        query_params["updated_from"] = updated_from

    updated_to = _parse_dt(params.get("updated_to", ""))
    if updated_to is not None:
        where_conditions.append("s.updated_at <= $updated_to")
        query_params["updated_to"] = updated_to

    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    having_clause = "WHERE " + " AND ".join(having_conditions) if having_conditions else ""

    students = run_query(
        f"""
        MATCH (s:Student)
        {where_clause}
        OPTIONAL MATCH (s)-[:SUBMITTED]->(r:Report)
        WITH s, count(r) AS report_count, max(r.upload_date) AS last_upload
        {having_clause}
        RETURN s.id AS id, s.name AS name, s.surname AS surname, s.group AS group,
               report_count, last_upload, s.created_at AS created_at, s.updated_at AS updated_at
        ORDER BY s.surname
        """,
        query_params,
    )

    for s in students:
        s["created_at_str"] = _fmt_ts(s.get("created_at"))
        s["updated_at_str"] = _fmt_ts(s.get("updated_at"))
        s["last_upload_str"] = _fmt_ts(s.get("last_upload"))

    return templates.TemplateResponse(
        "students.html",
        {"request": request, "user": user, "students": students, "params": params},
    )


@router.get("/new")
async def new_student_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("student_new.html", {"request": request, "user": user})


@router.post("/new")
async def create_student(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    group: int = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    sid = _next_id()
    now = int(time.time())
    run_write(
        "CREATE (s:Student {id:$id, name:$name, surname:$surname, group:$group, created_at:$ts, updated_at:$ts})",
        {"id": sid, "name": name, "surname": surname, "group": group, "ts": now},
    )
    return RedirectResponse(url="/students/", status_code=302)


@router.get("/{student_id}")
async def student_detail(request: Request, student_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    result = run_query("MATCH (s:Student {id:$id}) RETURN s", {"id": student_id})
    if not result:
        raise HTTPException(status_code=404, detail="Student not found")

    s = dict(result[0]["s"])
    s["created_at_str"] = _fmt_ts(s.get("created_at"))
    s["updated_at_str"] = _fmt_ts(s.get("updated_at"))

    reports = run_query(
        """
        MATCH (s:Student {id:$id})-[:SUBMITTED]->(r:Report)
        RETURN r.id AS id, r.title AS title, r.subject AS subject,
               r.originality AS originality, r.status AS status, r.upload_date AS upload_date
        ORDER BY r.upload_date DESC
        """,
        {"id": student_id},
    )

    for r in reports:
        r["upload_date_str"] = _fmt_ts(r.get("upload_date"))

    last_upload = max((r["upload_date"] for r in reports if r.get("upload_date")), default=None)
    s["last_upload_str"] = _fmt_ts(last_upload)

    return templates.TemplateResponse(
        "student_detail.html",
        {"request": request, "user": user, "student": s, "reports": reports},
    )


@router.get("/{student_id}/edit")
async def edit_student_page(request: Request, student_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    result = run_query("MATCH (s:Student {id:$id}) RETURN s", {"id": student_id})
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    s = dict(result[0]["s"])
    return templates.TemplateResponse("student_edit.html", {"request": request, "user": user, "student": s})


@router.post("/{student_id}/edit")
async def edit_student_submit(
    request: Request,
    student_id: int,
    name: str = Form(...),
    surname: str = Form(...),
    group: int = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    run_write(
        "MATCH (s:Student {id:$id}) SET s.name=$name, s.surname=$surname, s.group=$group, s.updated_at=$ts",
        {"id": student_id, "name": name, "surname": surname, "group": group, "ts": int(time.time())},
    )
    return RedirectResponse(url=f"/students/{student_id}", status_code=302)


@router.post("/{student_id}/delete")
async def delete_student(request: Request, student_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    run_write("MATCH (s:Student {id:$id}) DETACH DELETE s", {"id": student_id})
    return RedirectResponse(url="/students/", status_code=302)
