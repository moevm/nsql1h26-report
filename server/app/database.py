import os
import time
import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://db:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def wait_for_neo4j(retries: int = 30, delay: float = 3.0):
    for attempt in range(retries):
        try:
            drv = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            drv.verify_connectivity()
            drv.close()
            logger.info("Neo4j is ready.")
            return
        except Exception as e:
            logger.warning(f"Neo4j not ready ({attempt + 1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to Neo4j after multiple retries")


def init_db():
    with get_driver().session() as session:
        session.run("CREATE CONSTRAINT student_id IF NOT EXISTS FOR (s:Student) REQUIRE s.id IS UNIQUE")
        session.run("CREATE CONSTRAINT report_id IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE")
        session.run("CREATE CONSTRAINT part_id IF NOT EXISTS FOR (p:Part) REQUIRE p.id IS UNIQUE")
        session.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
        session.run("CREATE INDEX chunk_hash IF NOT EXISTS FOR (c:Chunk) ON (c.hash)")
    logger.info("DB indexes created.")


def run_query(query: str, params: dict = None):
    with get_driver().session() as session:
        result = session.run(query, params or {})
        return [dict(record) for record in result]


def run_write(query: str, params: dict = None):
    with get_driver().session() as session:
        result = session.run(query, params or {})
        return result.consume()
