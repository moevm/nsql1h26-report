from fastapi import FastAPI
from neo4j import GraphDatabase
import uuid
from datetime import datetime

app = FastAPI()

NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

@app.get("/")
def root():
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            msg_id = str(uuid.uuid4())
            session.run(
                "CREATE (n:Test {id: $id, text: 'Hello World', time: $time})",
                id=msg_id,
                time=str(datetime.now())
            )
            
            result = session.run(
                "MATCH (n:Test) RETURN n ORDER BY n.time DESC LIMIT 1"
            )
            data = result.single()
            last = data["n"] if data else None
            
            return {
                "written": msg_id,
                "read": last,
                "status": "success"
            }
    finally:
        driver.close()