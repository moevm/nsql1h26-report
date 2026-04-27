import time
import json
import datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query, run_write
from server.app.services.text_processor import process_docx

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="client/templates")


def _next_id(label: str) -> int:
    result = run_query(f"MATCH (n:{label}) RETURN max(n.id) AS max_id")
    max_id = result[0]["max_id"] if result and result[0]["max_id"] is not None else 0
    return int(max_id) + 1


def _store_report(data: dict, student_id: Optional[int] = None) -> int:
    report_id = _next_id("Report")
    run_write(
        """
        CREATE (r:Report {
            id: $id, title: $title, author: $author, group: $group,
            subject: $subject, words_count: $words_count, flesh_index: $flesh_index,
            keyword_density: $keyword_density, originality: $originality,
            conclusion: $conclusion, bibliography: $bibliography,
            introduction: $introduction, status: $status,
            upload_date: $upload_date, comment: $comment
        })
        """,
        {
            "id": report_id,
            "title": data["title"],
            "author": data["author"],
            "group": data["group"],
            "subject": data["subject"],
            "words_count": data["words_count"],
            "flesh_index": data["flesh_index"],
            "keyword_density": data["keyword_density"],
            "originality": 100.0,
            "conclusion": data["conclusion"],
            "bibliography": data["bibliography"],
            "introduction": data["introduction"],
            "status": "Готов",
            "upload_date": int(time.time()),
            "comment": data.get("comment", ""),
        },
    )

    if student_id:
        run_write(
            "MATCH (s:Student {id:$sid}), (r:Report {id:$rid}) MERGE (s)-[:SUBMITTED]->(r)",
            {"sid": student_id, "rid": report_id},
        )

    part_id_base = _next_id("Part")
    chunk_id_counter = _next_id("Chunk")

    for i, part in enumerate(data.get("parts", [])):
        part_id = part_id_base + i
        run_write(
            "MERGE (p:Part {id:$id}) SET p.type=$type",
            {"id": part_id, "type": part["type"]},
        )
        run_write(
            "MATCH (r:Report {id:$rid}), (p:Part {id:$pid}) MERGE (r)-[:HAS_PART]->(p)",
            {"rid": report_id, "pid": part_id},
        )

        for chunk in part.get("chunks", []):
            existing = run_query(
                "MATCH (c:Chunk {hash:$hash}) RETURN c.id AS id LIMIT 1",
                {"hash": chunk["hash"]},
            )
            if existing:
                cid = existing[0]["id"]
            else:
                cid = chunk_id_counter
                chunk_id_counter += 1
                run_write(
                    "MERGE (c:Chunk {id:$id}) SET c.text=$text, c.hash=$hash",
                    {"id": cid, "text": chunk["text"], "hash": chunk["hash"]},
                )

            run_write(
                "MATCH (p:Part {id:$pid}), (c:Chunk {id:$cid}) MERGE (p)-[:CONTAINS]->(c)",
                {"pid": part_id, "cid": cid},
            )

    run_write(
        """
        MATCH (r:Report {id:$rid})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c:Chunk)
        WITH r, c, count{ (c)<-[:CONTAINS]-(:Part)<-[:HAS_PART]-(:Report) } AS usage_count
        WITH r, count(c) AS total_chunks,
             sum(CASE WHEN usage_count = 1 THEN 1 ELSE 0 END) AS unique_chunks
        SET r.originality = CASE WHEN total_chunks > 0
            THEN round((toFloat(unique_chunks) / total_chunks) * 100.0, 1)
            ELSE 100.0 END
        """,
        {"rid": report_id},
    )

    return report_id


@router.get("/new")
async def new_report_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    students = run_query("MATCH (s:Student) RETURN s.id AS id, s.name AS name, s.surname AS surname, s.group AS group ORDER BY s.surname")
    return templates.TemplateResponse("report_new.html", {"request": request, "user": user, "students": students})


@router.post("/upload")
async def upload_report(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    group: int = Form(...),
    subject: str = Form(...),
    student_id: Optional[int] = Form(None),
    comment: str = Form(""),
    file: Optional[UploadFile] = File(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if file and file.filename and file.filename.endswith(".docx"):
        content = await file.read()
        try:
            data = process_docx(content, title, author, group, subject)
            data["comment"] = comment
        except Exception as e:
            data = {
                "title": title, "author": author, "group": group, "subject": subject,
                "comment": comment, "parts": [], "words_count": 0,
                "flesh_index": 0, "keyword_density": 0,
                "introduction": False, "conclusion": False, "bibliography": False,
            }
    else:
        data = {
            "title": title, "author": author, "group": group, "subject": subject,
            "comment": comment, "parts": [], "words_count": 0,
            "flesh_index": 0, "keyword_density": 0,
            "introduction": False, "conclusion": False, "bibliography": False,
        }

    report_id = _store_report(data, student_id)
    return RedirectResponse(url=f"/reports/{report_id}", status_code=302)


@router.get("/{report_id}")
async def report_detail(request: Request, report_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    result = run_query(
        """
        MATCH (r:Report {id:$id})
        OPTIONAL MATCH (s:Student)-[:SUBMITTED]->(r)
        RETURN r, s
        """,
        {"id": report_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")

    r = dict(result[0]["r"])
    s = dict(result[0]["s"]) if result[0]["s"] else None

    ts = r.get("upload_date")
    r["upload_date_str"] = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else "—"

    plagiarism_suspects = run_query(
        """
        MATCH (r1:Report {id:$rid})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c:Chunk)
              <-[:CONTAINS]-(:Part)<-[:HAS_PART]-(r2:Report)
        WHERE r1 <> r2
        RETURN r2.id AS suspect_id, r2.title AS suspect_title,
               r2.author AS suspect_author, count(c) AS shared_chunks
        ORDER BY shared_chunks DESC
        LIMIT 5
        """,
        {"rid": report_id},
    )

    return templates.TemplateResponse(
        "report_detail.html",
        {"request": request, "user": user, "report": r, "student": s, "suspects": plagiarism_suspects},
    )


@router.get("/{report_id}/edit")
async def edit_report_page(request: Request, report_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    result = run_query("MATCH (r:Report {id:$id}) RETURN r", {"id": report_id})
    if not result:
        raise HTTPException(status_code=404, detail="Not found")

    r = dict(result[0]["r"])
    students = run_query("MATCH (s:Student) RETURN s.id AS id, s.name AS name, s.surname AS surname, s.group AS group ORDER BY s.surname")
    student_result = run_query(
        "MATCH (s:Student)-[:SUBMITTED]->(r:Report {id:$id}) RETURN s.id AS sid",
        {"id": report_id},
    )
    current_sid = student_result[0]["sid"] if student_result else None

    return templates.TemplateResponse(
        "report_edit.html",
        {"request": request, "user": user, "report": r, "students": students, "current_sid": current_sid},
    )


@router.post("/{report_id}/edit")
async def edit_report_submit(
    request: Request,
    report_id: int,
    title: str = Form(...),
    author: str = Form(...),
    group: int = Form(...),
    subject: str = Form(...),
    comment: str = Form(""),
    student_id: Optional[int] = Form(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    run_write(
        "MATCH (r:Report {id:$id}) SET r.title=$title, r.author=$author, r.group=$group, r.subject=$subject, r.comment=$comment",
        {"id": report_id, "title": title, "author": author, "group": group, "subject": subject, "comment": comment},
    )

    if student_id:
        run_write("MATCH (s:Student)-[rel:SUBMITTED]->(r:Report {id:$rid}) DELETE rel", {"rid": report_id})
        run_write(
            "MATCH (s:Student {id:$sid}), (r:Report {id:$rid}) MERGE (s)-[:SUBMITTED]->(r)",
            {"sid": student_id, "rid": report_id},
        )

    return RedirectResponse(url=f"/reports/{report_id}", status_code=302)


@router.post("/{report_id}/delete")
async def delete_report(request: Request, report_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    run_write(
        """
        MATCH (r:Report {id:$id})-[:HAS_PART]->(p:Part)-[:CONTAINS]->(c:Chunk)
        WITH r, p, c
        WHERE NOT exists { (c)<-[:CONTAINS]-(:Part)<-[:HAS_PART]-(:Report) WHERE id(r) <> $id }
        DETACH DELETE c
        """,
        {"id": report_id},
    )
    run_write(
        "MATCH (r:Report {id:$id})-[:HAS_PART]->(p:Part) DETACH DELETE p",
        {"id": report_id},
    )
    run_write("MATCH (r:Report {id:$id}) DETACH DELETE r", {"id": report_id})
    return RedirectResponse(url="/dashboard", status_code=302)
