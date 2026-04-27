from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(prefix="/statistics", tags=["statistics"])
templates = Jinja2Templates(directory="client/templates")


@router.get("/")
async def statistics_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    groups = run_query("MATCH (r:Report) RETURN DISTINCT r.group AS g ORDER BY g")
    group_list = [row["g"] for row in groups if row["g"]]

    selected_group = request.query_params.get("group", "")
    metrics = request.query_params.getlist("metrics")

    stats = []
    if selected_group or not selected_group:
        where = "WHERE r.group = $g" if selected_group else ""
        params = {"g": int(selected_group)} if selected_group else {}

        stats = run_query(
            f"""
            MATCH (s:Student)-[:SUBMITTED]->(r:Report)
            {where}
            RETURN
                r.group AS group,
                count(r) AS report_count,
                round(avg(r.words_count), 0) AS avg_words,
                round(avg(r.originality), 1) AS avg_originality,
                round(avg(r.flesh_index), 1) AS avg_flesh,
                sum(CASE WHEN r.bibliography THEN 1 ELSE 0 END) AS has_bibliography,
                sum(CASE WHEN r.introduction THEN 1 ELSE 0 END) AS has_introduction,
                sum(CASE WHEN r.conclusion THEN 1 ELSE 0 END) AS has_conclusion,
                min(r.originality) AS min_originality,
                max(r.originality) AS max_originality
            ORDER BY group
            """,
            params,
        )

    report_rows = []
    if selected_group:
        report_rows = run_query(
            """
            MATCH (s:Student)-[:SUBMITTED]->(r:Report {group:$g})
            RETURN s.name + ' ' + s.surname AS student,
                   r.title AS title, r.words_count AS words,
                   r.originality AS originality, r.flesh_index AS flesh,
                   r.bibliography AS bib, r.introduction AS intro, r.conclusion AS conc
            ORDER BY r.title
            """,
            {"g": int(selected_group)},
        )

    return templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "user": user,
            "groups": group_list,
            "selected_group": selected_group,
            "metrics": metrics,
            "stats": stats,
            "report_rows": report_rows,
        },
    )
