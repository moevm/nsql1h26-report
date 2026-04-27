from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(prefix="/plagiarism", tags=["plagiarism"])
templates = Jinja2Templates(directory="client/templates")


def _get_report_chunks(report_id: int) -> list:
    return run_query(
        """
        MATCH (r:Report {id:$rid})-[:HAS_PART]->(p:Part)-[:CONTAINS]->(c:Chunk)
        RETURN c.id AS id, c.text AS text, c.hash AS hash, p.type AS part_type
        ORDER BY p.id, c.id
        """,
        {"rid": report_id},
    )


@router.get("/{report_id}")
async def plagiarism_page(request: Request, report_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    report_result = run_query("MATCH (r:Report {id:$id}) RETURN r", {"id": report_id})
    if not report_result:
        raise HTTPException(status_code=404, detail="Report not found")

    report = dict(report_result[0]["r"])
    
    suspects = run_query(
        """
        MATCH (r1:Report {id:$rid})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c:Chunk)
              <-[:CONTAINS]-(:Part)<-[:HAS_PART]-(r2:Report)
        WHERE r1 <> r2
        RETURN r2.id AS suspect_id, r2.title AS suspect_title,
               r2.author AS suspect_author, count(c) AS shared_chunks
        ORDER BY shared_chunks DESC
        LIMIT 10
        """,
        {"rid": report_id},
    )

    return templates.TemplateResponse(
        "plagiarism.html",
        {
            "request": request,
            "user": user,
            "report": report,
            "suspects": suspects,
        },
    )


@router.get("/{report_id}/compare/{source_id}")
async def compare_reports(request: Request, report_id: int, source_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    report_result = run_query("MATCH (r:Report {id:$id}) RETURN r", {"id": report_id})
    source_result = run_query("MATCH (r:Report {id:$id}) RETURN r", {"id": source_id})

    if not report_result or not source_result:
        raise HTTPException(status_code=404, detail="Report not found")

    report = dict(report_result[0]["r"])
    source = dict(source_result[0]["r"])

    shared = run_query(
        """
        MATCH (r1:Report {id:$rid1})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c1:Chunk)
        MATCH (r2:Report {id:$rid2})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c2:Chunk)
        WHERE c1.hash = c2.hash
        RETURN DISTINCT c1.hash AS hash
        """,
        {"rid1": report_id, "rid2": source_id},
    )
    shared_hashes = {r["hash"] for r in shared}

    report_chunks = _get_report_chunks(report_id)
    source_chunks = _get_report_chunks(source_id)

    total_r = len(report_chunks)
    shared_r = sum(1 for c in report_chunks if c["hash"] in shared_hashes)
    borrow_pct = round(shared_r / total_r * 100) if total_r else 0
    orig_pct = 100 - borrow_pct

    return templates.TemplateResponse(
        "compare.html",
        {
            "request": request,
            "user": user,
            "report": report,
            "source": source,
            "report_chunks": report_chunks,
            "source_chunks": source_chunks,
            "shared_hashes": list(shared_hashes),
            "borrow_pct": borrow_pct,
            "orig_pct": orig_pct,
        },
    )
