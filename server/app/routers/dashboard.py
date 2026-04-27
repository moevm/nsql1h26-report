from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="client/templates")


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
               s.id AS student_id
        ORDER BY r.upload_date DESC
        """
    )

    import datetime
    for r in reports:
        ts = r.get("upload_date")
        if ts:
            r["upload_date_str"] = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y")
        else:
            r["upload_date_str"] = "—"

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "reports": reports},
    )
