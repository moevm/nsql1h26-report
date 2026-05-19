import datetime
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="client/templates")
PAGE_SIZE = 5


def _fmt_size(b):
    if b is None:
        return "—"
    if b >= 1024 * 1024:
        return f"{b/1024/1024:.1f} МБ"
    if b >= 1024:
        return f"{b/1024:.1f} КБ"
    return f"{b} Б"


@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    groups_raw = run_query("MATCH (r:Report) RETURN DISTINCT r.group AS g ORDER BY g")
    all_groups = [row["g"] for row in groups_raw if row["g"]]

    selected_groups = [int(g) for g in request.query_params.getlist("group") if g.isdigit()]

    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    group_cond = "WHERE r.group IN $groups" if selected_groups else ""
    q_params = {"groups": selected_groups} if selected_groups else {}

    total_res = run_query(
        f"MATCH (r:Report) {group_cond} RETURN count(r) AS cnt", q_params
    )
    total = total_res[0]["cnt"] if total_res else 0
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    reports = run_query(
        f"""
        MATCH (r:Report) {group_cond}
        OPTIONAL MATCH (s:Student)-[:SUBMITTED]->(r)
        RETURN r.id AS id, r.title AS title, r.author AS author,
               r.group AS group, r.subject AS subject, r.status AS status,
               r.words_count AS words_count, r.flesh_index AS flesh_index,
               r.originality AS originality, r.upload_date AS upload_date,
               r.file_size AS file_size, r.comment AS comment
        ORDER BY r.upload_date DESC
        SKIP $skip LIMIT $limit
        """,
        {**q_params, "skip": (page - 1) * PAGE_SIZE, "limit": PAGE_SIZE},
    )

    for r in reports:
        ts = r.get("upload_date")
        r["upload_date_str"] = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else "—"
        r["file_size_str"] = _fmt_size(r.get("file_size"))

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "reports": reports,
        "all_groups": all_groups, "selected_groups": selected_groups,
        "total": total, "page": page, "total_pages": total_pages, "page_size": PAGE_SIZE,
    })
