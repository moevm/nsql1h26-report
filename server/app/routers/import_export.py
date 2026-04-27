import json
import time
import hashlib
from io import BytesIO
from typing import List

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query, run_write
from server.app.services.text_processor import process_docx

router = APIRouter(tags=["import_export"])
templates = Jinja2Templates(directory="client/templates")

@router.get("/import")
async def import_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mass_import.html", {"request": request, "user": user})


@router.post("/import/upload")
async def mass_upload(
    request: Request,
    files: List[UploadFile] = File(...),
    default_group: int = Form(3341),
    default_subject: str = Form("Программирование"),
):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    results = []

    for f in files:
        if not f.filename.endswith(".docx"):
            results.append({"filename": f.filename, "status": "Ошибка", "detail": "Не .docx файл"})
            continue
        try:
            content = await f.read()
            title = f.filename.replace(".docx", "")
            author = title
            data = process_docx(content, title, author, default_group, default_subject)

            report_id = _store_report_from_data(data)
            results.append({"filename": f.filename, "status": "Готов", "report_id": report_id})
        except Exception as e:
            results.append({"filename": f.filename, "status": "Ошибка", "detail": str(e)})

    return JSONResponse({"results": results})


def _next_id(label: str) -> int:
    result = run_query(f"MATCH (n:{label}) RETURN max(n.id) AS m")
    m = result[0]["m"] if result and result[0]["m"] is not None else 0
    return int(m) + 1


def _store_report_from_data(data: dict) -> int:
    report_id = _next_id("Report")
    run_write(
        """
        CREATE (r:Report {
            id:$id, title:$title, author:$author, group:$group,
            subject:$subject, words_count:$wc, flesh_index:$fi,
            keyword_density:$kd, originality:100.0,
            conclusion:$conc, bibliography:$bib, introduction:$intro,
            status:'Готов', upload_date:$ts, comment:''
        })
        """,
        {
            "id": report_id, "title": data["title"], "author": data["author"],
            "group": data["group"], "subject": data["subject"],
            "wc": data["words_count"], "fi": data["flesh_index"],
            "kd": data["keyword_density"], "conc": data["conclusion"],
            "bib": data["bibliography"], "intro": data["introduction"],
            "ts": int(time.time()),
        },
    )

    part_base = _next_id("Part")
    chunk_ctr = _next_id("Chunk")

    for i, part in enumerate(data.get("parts", [])):
        pid = part_base + i
        run_write("MERGE (p:Part {id:$id}) SET p.type=$t", {"id": pid, "t": part["type"]})
        run_write(
            "MATCH (r:Report {id:$rid}),(p:Part {id:$pid}) MERGE (r)-[:HAS_PART]->(p)",
            {"rid": report_id, "pid": pid},
        )
        for chunk in part.get("chunks", []):
            ex = run_query("MATCH (c:Chunk {hash:$h}) RETURN c.id AS id LIMIT 1", {"h": chunk["hash"]})
            if ex:
                cid = ex[0]["id"]
            else:
                cid = chunk_ctr
                chunk_ctr += 1
                run_write(
                    "MERGE (c:Chunk {id:$id}) SET c.text=$t, c.hash=$h",
                    {"id": cid, "t": chunk["text"], "h": chunk["hash"]},
                )
            run_write(
                "MATCH (p:Part {id:$pid}),(c:Chunk {id:$cid}) MERGE (p)-[:CONTAINS]->(c)",
                {"pid": pid, "cid": cid},
            )

    run_write(
        """
        MATCH (r:Report {id:$rid})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c:Chunk)
        WITH r, c, count{(c)<-[:CONTAINS]-(:Part)<-[:HAS_PART]-(:Report)} AS u
        WITH r, count(c) AS tot, sum(CASE WHEN u=1 THEN 1 ELSE 0 END) AS uniq
        SET r.originality = CASE WHEN tot>0 THEN round((toFloat(uniq)/tot)*100.0,1) ELSE 100.0 END
        """,
        {"rid": report_id},
    )
    return report_id

@router.get("/export")
async def export_all(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    students = run_query("MATCH (s:Student) RETURN s{.*} AS s ORDER BY s.id")
    reports = run_query("MATCH (r:Report) RETURN r{.*} AS r ORDER BY r.id")
    parts = run_query("MATCH (p:Part) RETURN p{.*} AS p ORDER BY p.id")
    chunks = run_query("MATCH (c:Chunk) RETURN c{.*} AS c ORDER BY c.id")

    submitted = run_query(
        "MATCH (s:Student)-[:SUBMITTED]->(r:Report) RETURN s.id AS student_id, r.id AS report_id"
    )
    has_part = run_query(
        "MATCH (r:Report)-[:HAS_PART]->(p:Part) RETURN r.id AS report_id, p.id AS part_id"
    )
    contains = run_query(
        "MATCH (p:Part)-[:CONTAINS]->(c:Chunk) RETURN p.id AS part_id, c.id AS chunk_id"
    )

    export_data = {
        "students": [r["s"] for r in students],
        "reports": [r["r"] for r in reports],
        "parts": [r["p"] for r in parts],
        "chunks": [r["c"] for r in chunks],
        "relationships": {
            "submitted": [{"student_id": r["student_id"], "report_id": r["report_id"]} for r in submitted],
            "has_part": [{"report_id": r["report_id"], "part_id": r["part_id"]} for r in has_part],
            "contains": [{"part_id": r["part_id"], "chunk_id": r["chunk_id"]} for r in contains],
        },
    }

    content = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)
    return StreamingResponse(
        BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=export.json"},
    )

@router.post("/import/json")
async def import_json(request: Request, file: UploadFile = File(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        return JSONResponse({"error": "Неверный формат JSON"}, status_code=400)

    run_write("MATCH (n) DETACH DELETE n")

    for s in data.get("students", []):
        run_write(
            "MERGE (s:Student {id:$id}) SET s.name=$name, s.surname=$surname, s.group=$group",
            {"id": s["id"], "name": s["name"], "surname": s["surname"], "group": s["group"]},
        )

    for r in data.get("reports", []):
        run_write(
            """
            MERGE (r:Report {id:$id})
            SET r.title=$title, r.author=$author, r.group=$group,
                r.subject=$subject, r.words_count=$wc, r.flesh_index=$fi,
                r.keyword_density=$kd, r.originality=$orig,
                r.conclusion=$conc, r.bibliography=$bib, r.introduction=$intro,
                r.status=$status, r.upload_date=$ud, r.comment=$comment
            """,
            {
                "id": r["id"], "title": r.get("title",""), "author": r.get("author",""),
                "group": r.get("group", 0), "subject": r.get("subject",""),
                "wc": r.get("words_count",0), "fi": r.get("flesh_index",0),
                "kd": r.get("keyword_density",0), "orig": r.get("originality",100.0),
                "conc": r.get("conclusion", False), "bib": r.get("bibliography", False),
                "intro": r.get("introduction", False), "status": r.get("status","Готов"),
                "ud": r.get("upload_date", int(time.time())), "comment": r.get("comment",""),
            },
        )

    for p in data.get("parts", []):
        run_write("MERGE (p:Part {id:$id}) SET p.type=$t", {"id": p["id"], "t": p.get("type","")})

    for c in data.get("chunks", []):
        run_write(
            "MERGE (c:Chunk {id:$id}) SET c.text=$t, c.hash=$h",
            {"id": c["id"], "t": c.get("text",""), "h": c.get("hash","")},
        )

    rels = data.get("relationships", {})
    for rel in rels.get("submitted", []):
        run_write(
            "MATCH (s:Student {id:$sid}),(r:Report {id:$rid}) MERGE (s)-[:SUBMITTED]->(r)",
            {"sid": rel["student_id"], "rid": rel["report_id"]},
        )
    for rel in rels.get("has_part", []):
        run_write(
            "MATCH (r:Report {id:$rid}),(p:Part {id:$pid}) MERGE (r)-[:HAS_PART]->(p)",
            {"rid": rel["report_id"], "pid": rel["part_id"]},
        )
    for rel in rels.get("contains", []):
        run_write(
            "MATCH (p:Part {id:$pid}),(c:Chunk {id:$cid}) MERGE (p)-[:CONTAINS]->(c)",
            {"pid": rel["part_id"], "cid": rel["chunk_id"]},
        )

    return JSONResponse({"status": "ok", "message": "Данные успешно импортированы"})
