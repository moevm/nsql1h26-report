import datetime
import json
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(prefix="/statistics", tags=["statistics"])
templates = Jinja2Templates(directory="client/templates")

X_FIELDS = {
    "group":   {"label": "Группа",        "expr": "toString(r.group)"},
    "subject": {"label": "Предмет",       "expr": "r.subject"},
    "status":  {"label": "Статус",        "expr": "r.status"},
    "author":  {"label": "Автор",         "expr": "r.author"},
}

Y_FIELDS = {
    "count":           {"label": "Кол-во отчётов",       "expr": "count(r)",               "fmt": "int"},
    "avg_originality": {"label": "Ср. оригинальность %", "expr": "round(avg(r.originality),1)", "fmt": "float"},
    "avg_words":       {"label": "Ср. кол-во слов",      "expr": "round(avg(r.words_count),0)", "fmt": "int"},
    "avg_flesh":       {"label": "Ср. индекс Флеша",     "expr": "round(avg(r.flesh_index),1)", "fmt": "float"},
}


def _build_filter(params: dict, selected_groups: list):
    conditions = []
    q = {}

    title = params.get("title", "").strip()
    if title:
        conditions.append("toLower(r.title) CONTAINS toLower($title)")
        q["title"] = title

    author = params.get("author", "").strip()
    if author:
        conditions.append("toLower(r.author) CONTAINS toLower($author)")
        q["author"] = author

    if selected_groups:
        conditions.append("r.group IN $groups")
        q["groups"] = selected_groups

    subject = params.get("subject", "").strip()
    if subject:
        conditions.append("toLower(r.subject) CONTAINS toLower($subject)")
        q["subject"] = subject

    status = params.get("status", "").strip()
    if status:
        conditions.append("r.status = $status")
        q["status"] = status

    date_from = params.get("date_from", "").strip()
    if date_from:
        try:
            q["ts_from"] = int(datetime.datetime.strptime(date_from, "%Y-%m-%dT%H:%M").timestamp())
            conditions.append("r.upload_date >= $ts_from")
        except ValueError:
            pass

    date_to = params.get("date_to", "").strip()
    if date_to:
        try:
            q["ts_to"] = int(datetime.datetime.strptime(date_to, "%Y-%m-%dT%H:%M").timestamp())
            conditions.append("r.upload_date <= $ts_to")
        except ValueError:
            pass

    min_orig = params.get("min_originality", "").strip()
    if min_orig:
        try:
            v = float(min_orig)
            if v > 0:
                conditions.append("r.originality >= $min_orig")
                q["min_orig"] = v
        except ValueError:
            pass

    max_orig = params.get("max_originality", "").strip()
    if max_orig:
        try:
            v = float(max_orig)
            if v < 100:
                conditions.append("r.originality <= $max_orig")
                q["max_orig"] = v
        except ValueError:
            pass

    min_flesh = params.get("min_flesh", "").strip()
    if min_flesh and min_flesh.isdigit() and int(min_flesh) > 0:
        conditions.append("r.flesh_index >= $min_flesh")
        q["min_flesh"] = int(min_flesh)

    max_flesh = params.get("max_flesh", "").strip()
    if max_flesh and max_flesh.isdigit() and int(max_flesh) < 100:
        conditions.append("r.flesh_index <= $max_flesh")
        q["max_flesh"] = int(max_flesh)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where, q


@router.get("/")
async def statistics_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    groups_raw = run_query("MATCH (r:Report) RETURN DISTINCT r.group AS g ORDER BY g")
    all_groups = [row["g"] for row in groups_raw if row["g"]]

    params = dict(request.query_params)
    selected_groups = [int(g) for g in request.query_params.getlist("group") if g.isdigit()]

    x_field = params.get("x_field", "group")
    y_field = params.get("y_field", "count")

    if x_field not in X_FIELDS:
        x_field = "group"
    if y_field not in Y_FIELDS:
        y_field = "count"

    where, q_params = _build_filter(params, selected_groups)
    x_expr = X_FIELDS[x_field]["expr"]
    y_expr = Y_FIELDS[y_field]["expr"]

    chart_data = None
    total_count = 0

    if params.get("x_field") or params.get("y_field") or selected_groups or any(
        params.get(k, "").strip() for k in ("title","author","subject","status","date_from","date_to","min_originality","max_originality","min_flesh","max_flesh")
    ):
        rows = run_query(
            f"""
            MATCH (r:Report) {where}
            WITH {x_expr} AS x_val, {y_expr} AS y_val
            WHERE x_val IS NOT NULL
            RETURN x_val, y_val
            ORDER BY x_val
            """,
            q_params,
        )

        total_res = run_query(f"MATCH (r:Report) {where} RETURN count(r) AS cnt", q_params)
        total_count = total_res[0]["cnt"] if total_res else 0

        fmt = Y_FIELDS[y_field]["fmt"]
        labels = [str(row["x_val"]) for row in rows]
        values = [int(row["y_val"] or 0) if fmt == "int" else float(row["y_val"] or 0) for row in rows]

        chart_data = json.dumps({"labels": labels, "values": values})

    return templates.TemplateResponse("statistics.html", {
        "request": request, "user": user,
        "all_groups": all_groups, "selected_groups": selected_groups,
        "params": params,
        "x_field": x_field, "y_field": y_field,
        "x_fields": X_FIELDS, "y_fields": Y_FIELDS,
        "chart_data": chart_data,
        "total_count": total_count,
        "x_label": X_FIELDS[x_field]["label"],
        "y_label": Y_FIELDS[y_field]["label"],
    })
