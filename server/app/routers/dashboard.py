import datetime

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="client/templates")


def _fmt_size(size_bytes):
    if size_bytes is None:
        return "—"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} МБ"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    return f"{size_bytes} Б"


@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    reports = run_query(
        """
        MATCH (r:Report)
        OPTIONAL MATCH (s:Student)-[:SUBMITTED]->(r)
        RETURN r.id AS id, r.title AS title, r.author AS author,
               r.group AS group, r.subject AS subject, r.status AS status,
               r.words_count AS words_count, r.flesh_index AS flesh_index,
               r.originality AS originality, r.upload_date AS upload_date,
               r.file_size AS file_size, r.comment AS comment,
               s.id AS student_id
        ORDER BY r.upload_date DESC
        """
    )

    for r in reports:
        ts = r.get("upload_date")
        r["upload_date_str"] = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else "—"
        r["file_size_str"] = _fmt_size(r.get("file_size"))

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "reports": reports},
    )
