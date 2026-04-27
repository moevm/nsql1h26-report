import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.app.database import wait_for_neo4j, init_db
from server.app.services.seeder import seed_data
from server.app import auth
from server.app.routers import dashboard, reports, students, search, graph, plagiarism, import_export, statistics

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_neo4j()
    init_db()
    seed_data()
    yield


app = FastAPI(title="Anti-Plagiarism System", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="client/static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(students.router)
app.include_router(search.router)
app.include_router(graph.router)
app.include_router(plagiarism.router)
app.include_router(import_export.router)
app.include_router(statistics.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard", status_code=302)
