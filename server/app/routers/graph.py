from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from server.app.auth import get_current_user
from server.app.database import run_query

router = APIRouter(prefix="/graph", tags=["graph"])
templates = Jinja2Templates(directory="client/templates")


@router.get("/{report_id}")
async def graph_page(request: Request, report_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    result = run_query("MATCH (r:Report {id:$id}) RETURN r.title AS title", {"id": report_id})
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")

    return templates.TemplateResponse(
        "graph.html",
        {"request": request, "user": user, "report_id": report_id, "report_title": result[0]["title"]},
    )


@router.get("/{report_id}/data")
async def graph_data(request: Request, report_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    nodes = []
    edges = []

    report_result = run_query(
        "MATCH (r:Report {id:$id}) RETURN r.id AS id, r.title AS title, r.author AS author",
        {"id": report_id},
    )
    if not report_result:
        return JSONResponse({"nodes": [], "edges": []})

    r = report_result[0]
    nodes.append({
        "data": {
            "id": f"r_{report_id}",
            "label": r["title"][:30] + ("..." if len(r["title"]) > 30 else ""),
            "type": "Report",
            "full_label": r["title"],
        }
    })

    parts = run_query(
        "MATCH (r:Report {id:$id})-[:HAS_PART]->(p:Part) RETURN p.id AS id, p.type AS type",
        {"id": report_id},
    )

    for part in parts:
        part_node_id = f"p_{part['id']}"
        nodes.append({
            "data": {
                "id": part_node_id,
                "label": part["type"][:20],
                "type": "Part",
                "full_label": part["type"],
            }
        })
        edges.append({
            "data": {
                "id": f"e_r{report_id}_p{part['id']}",
                "source": f"r_{report_id}",
                "target": part_node_id,
                "label": "HAS_PART",
            }
        })

        chunks = run_query(
            """
            MATCH (p:Part {id:$pid})-[:CONTAINS]->(c:Chunk)
            RETURN c.id AS id, c.text AS text,
                   count{ (c)<-[:CONTAINS]-(:Part)<-[:HAS_PART]-(:Report) } AS usage
            LIMIT 8
            """,
            {"pid": part["id"]},
        )

        for chunk in chunks:
            chunk_node_id = f"c_{chunk['id']}"
            is_shared = chunk["usage"] > 1
            label_text = chunk["text"][:25] + "..." if len(chunk["text"]) > 25 else chunk["text"]
            nodes.append({
                "data": {
                    "id": chunk_node_id,
                    "label": label_text,
                    "type": "SharedChunk" if is_shared else "Chunk",
                    "full_label": chunk["text"],
                    "shared": is_shared,
                }
            })
            edges.append({
                "data": {
                    "id": f"e_p{part['id']}_c{chunk['id']}",
                    "source": part_node_id,
                    "target": chunk_node_id,
                    "label": "CONTAINS",
                }
            })

    return JSONResponse({"nodes": nodes, "edges": edges})
