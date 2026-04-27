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


@router.get("/")
async def students_list(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    students = run_query(
        """
        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:SUBMITTED]->(r:Report)
        RETURN s.id AS id, s.name AS name, s.surname AS surname, s.group AS group,
               count(r) AS report_count
        ORDER BY s.surname
        """
    )
    return templates.TemplateResponse("students.html", {"request": request, "user": user, "students": students})


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
    run_write(
        "CREATE (s:Student {id:$id, name:$name, surname:$surname, group:$group})",
        {"id": sid, "name": name, "surname": surname, "group": group},
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
    reports = run_query(
        """
        MATCH (s:Student {id:$id})-[:SUBMITTED]->(r:Report)
        RETURN r.id AS id, r.title AS title, r.subject AS subject,
               r.originality AS originality, r.status AS status
        ORDER BY r.upload_date DESC
        """,
        {"id": student_id},
    )
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
        "MATCH (s:Student {id:$id}) SET s.name=$name, s.surname=$surname, s.group=$group",
        {"id": student_id, "name": name, "surname": surname, "group": group},
    )
    return RedirectResponse(url=f"/students/{student_id}", status_code=302)


@router.post("/{student_id}/delete")
async def delete_student(request: Request, student_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    run_write("MATCH (s:Student {id:$id}) DETACH DELETE s", {"id": student_id})
    return RedirectResponse(url="/students/", status_code=302)
