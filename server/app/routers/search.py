import datetime

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(prefix="/search", tags=["search"])
templates = Jinja2Templates(directory="client/templates")


@router.get("/")
async def search_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    params = dict(request.query_params)
    results = None

    if any(params.values()):
        results = _do_search(params)

    return templates.TemplateResponse(
        "search.html",
        {"request": request, "user": user, "params": params, "results": results},
    )


def _do_search(params: dict) -> list:
    conditions = []
    query_params = {}

    title = params.get("title", "").strip()
    if title:
        conditions.append("toLower(r.title) CONTAINS toLower($title)")
        query_params["title"] = title

    author = params.get("author", "").strip()
    if author:
        conditions.append("toLower(r.author) CONTAINS toLower($author)")
        query_params["author"] = author

    group = params.get("group", "").strip()
    if group and group.isdigit():
        conditions.append("r.group = $group")
        query_params["group"] = int(group)

    subject = params.get("subject", "").strip()
    if subject:
        conditions.append("toLower(r.subject) CONTAINS toLower($subject)")
        query_params["subject"] = subject

    status = params.get("status", "").strip()
    if status:
        conditions.append("r.status = $status")
        query_params["status"] = status

    comment = params.get("comment", "").strip()
    if comment:
        conditions.append("toLower(r.comment) CONTAINS toLower($comment)")
        query_params["comment"] = comment

    date_from = params.get("date_from", "").strip()
    if date_from:
        try:
            ts_from = int(datetime.datetime.strptime(date_from, "%Y-%m-%dT%H:%M").timestamp())
            conditions.append("r.upload_date >= $ts_from")
            query_params["ts_from"] = ts_from
        except ValueError:
            pass

    date_to = params.get("date_to", "").strip()
    if date_to:
        try:
            ts_to = int(datetime.datetime.strptime(date_to, "%Y-%m-%dT%H:%M").timestamp())
            conditions.append("r.upload_date <= $ts_to")
            query_params["ts_to"] = ts_to
        except ValueError:
            pass

    min_flesh = params.get("min_flesh", "").strip()
    if min_flesh and min_flesh.isdigit():
        conditions.append("r.flesh_index >= $min_flesh")
        query_params["min_flesh"] = int(min_flesh)

    max_flesh = params.get("max_flesh", "").strip()
    if max_flesh and max_flesh.isdigit() and int(max_flesh) < 100:
        conditions.append("r.flesh_index <= $max_flesh")
        query_params["max_flesh"] = int(max_flesh)

    min_originality = params.get("min_originality", "").strip()
    if min_originality:
        try:
            v = float(min_originality)
            if v > 0:
                conditions.append("r.originality >= $min_orig")
                query_params["min_orig"] = v
        except ValueError:
            pass

    max_originality = params.get("max_originality", "").strip()
    if max_originality:
        try:
            v = float(max_originality)
            if v < 100:
                conditions.append("r.originality <= $max_orig")
                query_params["max_orig"] = v
        except ValueError:
            pass

    word = params.get("word", "").strip()
    if word:
        base_query = f"""
        MATCH (r:Report)-[:HAS_PART]->(:Part)-[:CONTAINS]->(c:Chunk)
        WHERE toLower(c.text) CONTAINS toLower($word)
        {"AND " + " AND ".join(conditions) if conditions else ""}
        WITH DISTINCT r
        RETURN r.id AS id, r.title AS title, r.author AS author,
               r.group AS group, r.subject AS subject, r.status AS status,
               r.words_count AS words_count, r.flesh_index AS flesh_index,
               r.originality AS originality, r.upload_date AS upload_date
        ORDER BY r.title
        """
        query_params["word"] = word
    else:
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        base_query = f"""
        MATCH (r:Report)
        {where_clause}
        RETURN r.id AS id, r.title AS title, r.author AS author,
               r.group AS group, r.subject AS subject, r.status AS status,
               r.words_count AS words_count, r.flesh_index AS flesh_index,
               r.originality AS originality, r.upload_date AS upload_date
        ORDER BY r.title
        """

    rows = run_query(base_query, query_params)

    for r in rows:
        ts = r.get("upload_date")
        r["upload_date_str"] = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else "—"

    return rows
